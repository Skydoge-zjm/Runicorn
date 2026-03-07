from __future__ import annotations

import base64
import json
import logging
import os
import platform
import shutil
import socket
import sys
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from filelock import FileLock
from .config import get_user_root_dir
from .enabled import NoOpRun, is_enabled
from .workspace import get_workspace_root
from .assets.assets_json import ensure_assets_file, read_assets, update_assets_atomic
from .assets.archive import archive_dir, archive_file
from .assets.fingerprint import dir_stat_fingerprint, stat_fingerprint
from .assets.snapshot import snapshot_workspace
from .assets.outputs_scan import scan_outputs_once

# Setup logging
logger = logging.getLogger(__name__)

# Import modern storage components (graceful fallback if not available)
try:
    from .storage.backends import SQLiteStorageBackend
    from .storage.models import ExperimentRecord, MetricRecord
    from .storage.migration import ensure_modern_storage, detect_storage_type
    HAS_MODERN_STORAGE = True
    logger.info("Modern storage system available")
except ImportError as e:
    logger.debug(f"Modern storage not available: {e}")
    HAS_MODERN_STORAGE = False

# Optional: Import monitoring if needed
try:
    from .extensions.monitors import MetricMonitor, AnomalyDetector
    HAS_MONITORING = True
except ImportError:
    MetricMonitor = None
    AnomalyDetector = None
    HAS_MONITORING = False

# Optional: Import environment capture
try:
    from .extensions.environment import EnvironmentCapture
    HAS_ENV_CAPTURE = True
except ImportError:
    EnvironmentCapture = None
    HAS_ENV_CAPTURE = False

# Optional imports for image handling
try:
    from PIL import Image  # type: ignore
    HAS_PIL = True
except ImportError:
    Image = None  # type: ignore
    HAS_PIL = False
    logger.debug("Pillow not available, image features limited")

try:
    import numpy as np  # type: ignore
    HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    HAS_NUMPY = False
    logger.debug("NumPy not available, array image features limited")


DEFAULT_DIRNAME = ".runicorn"

_active_run_lock = threading.Lock()
_active_run: Optional["Run"] = None


def _now_ts() -> float:
    return time.time()


def _default_storage_dir(storage: Optional[str]) -> Path:
    # Priority:
    # 1) Explicit storage argument
    # 2) Environment variable RUNICORN_DIR
    # 3) Global user config (user_root_dir)
    # 4) Legacy local default ./.runicorn
    if storage:
        return Path(storage).expanduser().resolve()
    env = os.environ.get("RUNICORN_DIR")
    if env:
        return Path(env).expanduser().resolve()
    cfg = get_user_root_dir()
    if cfg:
        return cfg
    return (Path.cwd() / DEFAULT_DIRNAME).resolve()


def _gen_run_id() -> str:
    # timestamp + short random suffix for readability
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    suf = uuid.uuid4().hex[:6]
    return f"{ts}_{suf}"


def get_active_run() -> Optional["Run"]:
    return _active_run


def _normalize_path(path: Optional[str]) -> str:
    """Normalize experiment path.
    
    Args:
        path: User-provided path (e.g., "cv/yolo", "/", None)
        
    Returns:
        Normalized path (e.g., "cv/yolo", "", "default")
    """
    if path is None:
        return "default"
    
    # Normalize separators to forward slash
    path = path.replace("\\", "/")
    
    # Handle root path
    if path == "/" or path == "":
        return ""
    
    # Strip leading/trailing slashes
    path = path.strip("/")
    
    # Validate path characters
    import re
    if not re.match(r'^[a-zA-Z0-9_\-/]+$', path):
        raise ValueError(
            f"Invalid path: '{path}'. "
            "Path can only contain letters, numbers, underscores, hyphens, and forward slashes."
        )
    
    # Check for ".." to prevent directory traversal
    if ".." in path:
        raise ValueError(f"Invalid path: '{path}'. Path cannot contain '..'")
    
    # Check path length
    if len(path) > 200:
        raise ValueError(f"Path too long: {len(path)} characters. Maximum is 200.")
    
    return path


def _path_to_fs_path(path: str) -> str:
    """Convert normalized path to filesystem path using os.sep."""
    if not path:
        return ""
    return path.replace("/", os.sep)


# Valid SQLite statuses (schema.sql CHECK constraint)
_VALID_STATUSES = frozenset({"running", "finished", "failed", "interrupted"})

# Map common aliases to valid status values
_STATUS_ALIASES = {
    "completed": "finished",
    "success": "finished",
    "error": "failed",
    "crashed": "failed",
    "killed": "interrupted",
    "cancelled": "interrupted",
    "aborted": "interrupted",
}


def _normalize_status(status: str) -> str:
    """
    Normalize status to a valid SQLite schema value.
    
    Maps common aliases to valid values. Unknown statuses default to 'finished'
    since the user explicitly called finish().
    
    Valid values: 'running', 'finished', 'failed', 'interrupted'
    """
    s = (status or "").strip().lower()
    if s in _VALID_STATUSES:
        return s
    return _STATUS_ALIASES.get(s, "finished")


def _make_json_safe(obj: Any) -> Any:
    """
    Recursively convert non-JSON-serializable types to JSON-safe equivalents.
    Used by log_config() to handle Path, Enum, datetime, numpy, etc.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (set, frozenset)):
        return [_make_json_safe(x) for x in obj]
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if HAS_NUMPY and hasattr(np, "integer") and isinstance(obj, np.integer):
        return int(obj)
    if HAS_NUMPY and hasattr(np, "floating") and isinstance(obj, np.floating):
        return float(obj)
    if HAS_NUMPY and hasattr(np, "ndarray") and isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


@dataclass
class RunMeta:
    id: str
    path: str  # Flexible hierarchy path
    alias: Optional[str]
    created_at: float
    python: str
    platform: str
    hostname: str
    pid: int
    storage_dir: str
    workspace_root: str


class Run:
    def __init__(
        self,
        path: Optional[str] = None,
        storage: Optional[str] = None,
        run_id: Optional[str] = None,
        alias: Optional[str] = None,
        capture_env: bool = False,
        snapshot_code: bool = False,
        workspace_root: Optional[str] = None,
        snapshot_format: str = "zip",
        force_snapshot: bool = False,
        capture_console: bool = False,
        tqdm_mode: str = "smart",
    ) -> None:
        # Normalize and validate path
        self.path = _normalize_path(path)
        self.alias = alias
        
        # storage_root points to user_root_dir (or legacy ./.runicorn)
        self.storage_root = _default_storage_dir(storage)
        
        # Build run directory: storage_root/runs/<path>/<run_id>
        self.id = run_id or _gen_run_id()
        
        if self.path:
            fs_path = _path_to_fs_path(self.path)
            self.runs_dir = self.storage_root / "runs" / fs_path
        else:
            # Root path: storage_root/runs/
            self.runs_dir = self.storage_root / "runs"
        
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir = self.runs_dir / self.id
        self.media_dir = self.run_dir / "media"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)

        self._events_path = self.run_dir / "events.jsonl"
        self._summary_path = self.run_dir / "summary.json"
        self._status_path = self.run_dir / "status.json"
        self._meta_path = self.run_dir / "meta.json"
        self._logs_txt_path = self.run_dir / "logs.txt"  # for websocket tailing
        self._assets_path = self.run_dir / "assets.json"
        self._outputs_state_path = self.run_dir / ".outputs_state.json"

        # Separate locks for files
        self._events_lock = FileLock(str(self._events_path) + ".lock")
        self._summary_lock = FileLock(str(self._summary_path) + ".lock")
        self._status_lock = FileLock(str(self._status_path) + ".lock")
        self._logs_lock = FileLock(str(self._logs_txt_path) + ".lock")
        self._assets_lock = FileLock(str(self._assets_path) + ".lock")
        self._outputs_state_lock = FileLock(str(self._outputs_state_path) + ".lock")

        self.workspace_root = get_workspace_root(workspace_root)
        self._outputs_watch_thread: Optional[threading.Thread] = None
        self._outputs_watch_stop = threading.Event()
        self._finished = False

        # Global step counter for metrics logging
        # Starts from 0; first auto step will be 1
        self._global_step: int = 0
        
        # Primary metric tracking
        self._primary_metric_name: Optional[str] = None
        self._primary_metric_mode: str = "max"  # "max" or "min"
        self._best_metric_value: Optional[float] = None
        self._best_metric_step: Optional[int] = None
        
        # Initialize modern storage backend
        self.storage_backend = None
        
        # Allow disabling modern storage via environment variable (useful for testing)
        disable_modern_storage = os.environ.get("RUNICORN_DISABLE_MODERN_STORAGE", "").lower() in ("1", "true", "yes")
        
        if HAS_MODERN_STORAGE and not disable_modern_storage:
            try:
                self._init_modern_storage()
            except Exception as e:
                logger.warning(f"Failed to initialize modern storage: {e}, using file-only mode")
        
        # Optional monitoring
        self.monitor = None
        self.anomaly_detector = None
        if HAS_MONITORING:
            self.monitor = MetricMonitor()
            self.anomaly_detector = AnomalyDetector()

        meta = RunMeta(
            id=self.id,
            path=self.path,
            alias=self.alias,
            created_at=_now_ts(),
            python=sys.version.split(" ")[0],
            platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
            hostname=socket.gethostname(),
            pid=os.getpid(),
            storage_dir=str(self.storage_root),
            workspace_root=str(self.workspace_root),
        )
        self._write_json(self._meta_path, asdict(meta))
        self._write_json(self._status_path, {"status": "running", "started_at": _now_ts()})

        ensure_assets_file(self._assets_path)

        if snapshot_code:
            if snapshot_format != "zip":
                raise ValueError("snapshot_format currently only supports 'zip'")
            try:
                ws_root = self.workspace_root
                zip_path = self.run_dir / "code_snapshot.zip"
                snap = snapshot_workspace(ws_root, zip_path, force_snapshot=force_snapshot)
                archived = archive_file(zip_path, self.storage_root / "archive", category="code")

                def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
                    a["code"] = {
                        "snapshot": {
                            "saved": True,
                            "workspace_root": snap.get("workspace_root"),
                            "format": "zip",
                            "created_at": int(_now_ts()),
                            "archive_path": archived.get("archive_path"),
                            "fingerprint_kind": archived.get("fingerprint_kind"),
                            "fingerprint": archived.get("fingerprint"),
                        }
                    }
                    return a

                update_assets_atomic(self._assets_path, self._assets_lock, _upd)

                if self.storage_backend:
                    try:
                        self.storage_backend.record_asset_for_run(
                            run_id=self.id,
                            role="code",
                            asset_type="code_snapshot",
                            name="code_snapshot.zip",
                            source_uri=str(self.workspace_root),
                            archive_uri=archived.get("archive_path"),
                            is_archived=True,
                            fingerprint_kind=archived.get("fingerprint_kind"),
                            fingerprint=archived.get("fingerprint"),
                            created_at=float(meta.created_at),
                            metadata={
                                "format": "zip",
                                "workspace_root": str(self.workspace_root),
                            },
                        )
                    except Exception:
                        pass
            except Exception as snapshot_err:
                # Best-effort cleanup of the ghost run (BUG-41)
                try:
                    if self.run_dir.exists():
                        shutil.rmtree(self.run_dir, ignore_errors=True)
                    if self.storage_backend and hasattr(self.storage_backend, "delete_run_with_orphan_assets"):
                        self.storage_backend.delete_run_with_orphan_assets(self.id)
                except Exception:
                    pass
                raise snapshot_err

        if capture_env and HAS_ENV_CAPTURE:
            try:
                env_capture = EnvironmentCapture(working_dir=self.workspace_root)
                env_info = env_capture.capture_all()
                env_info.save(self.run_dir / "environment.json")
                logger.info(f"Environment captured for run {self.id}")
            except Exception as e:
                logger.warning(f"Failed to capture environment: {e}")

        # Console capture (initialized after _logs_txt_path is set)
        self._console_capture = None
        self._capture_console = capture_console
        self._tqdm_mode = tqdm_mode
        
        if capture_console:
            try:
                from .console import ConsoleCapture
                self._console_capture = ConsoleCapture(
                    log_path=self._logs_txt_path,
                    tqdm_mode=tqdm_mode,
                )
                self._console_capture.start()
                logger.debug(f"Console capture started for run {self.id}")
            except Exception as e:
                # Graceful degradation: log warning and continue without capture
                import warnings
                warnings.warn(
                    f"Failed to initialize console capture: {e}. "
                    "Continuing without capture.",
                    RuntimeWarning,
                    stacklevel=2
                )
                self._console_capture = None

    def scan_outputs_once(
        self,
        *,
        output_dirs: List[Union[str, Path]],
        patterns: Optional[List[str]] = None,
        stable_required: int = 2,
        min_age_sec: float = 1.0,
        mode: str = "rolling",
        log_snapshot_interval_sec: float = 60.0,
        state_gc_after_sec: float = 7 * 24 * 3600,
    ) -> Dict[str, Any]:
        if self._finished:
            logger.warning("scan_outputs_once called after finish(); ignoring")
            return {}
        res = scan_outputs_once(
            run_id=self.id,
            run_dir=self.run_dir,
            storage_root=self.storage_root,
            workspace_root=self.workspace_root,
            output_dirs=output_dirs,
            assets_path=self._assets_path,
            assets_lock=self._assets_lock,
            state_path=self._outputs_state_path,
            state_lock=self._outputs_state_lock,
            patterns=patterns,
            stable_required=stable_required,
            min_age_sec=min_age_sec,
            mode=mode,
            log_snapshot_interval_sec=log_snapshot_interval_sec,
            state_gc_after_sec=state_gc_after_sec,
            should_stop=lambda: self._finished or self._outputs_watch_stop.is_set(),
        )

        if self._finished or self._outputs_watch_stop.is_set():
            return res

        # BUG-30: When rolling output is updated (same key, new version), unlink old
        # asset before linking the new one to avoid stale SQLite relations
        if self.storage_backend:
            try:
                for e in res.get("archived_entries") or []:
                    key = e.get("key")
                    if key and hasattr(
                        self.storage_backend, "unlink_run_asset"
                    ):
                        assets = self.storage_backend.get_assets_for_run(self.id)
                        for a in assets:
                            if a.get("role") != "output":
                                continue
                            meta = a.get("metadata_json")
                            if isinstance(meta, str):
                                meta = json.loads(meta) if meta else {}
                            elif meta is None:
                                meta = {}
                            if meta.get("key") == key:
                                self.storage_backend.unlink_run_asset(
                                    self.id, a["asset_id"]
                                )
                                break
                    self.storage_backend.record_asset_for_run(
                        run_id=self.id,
                        role="output",
                        asset_type="output",
                        name=e.get("name"),
                        source_uri=e.get("path"),
                        archive_uri=e.get("archive_path"),
                        is_archived=True,
                        fingerprint_kind=e.get("fingerprint_kind"),
                        fingerprint=e.get("fingerprint"),
                        created_at=float(e.get("archived_at") or 0),
                        metadata={
                            "key": e.get("key"),
                            "kind": e.get("kind"),
                            "mode": e.get("mode"),
                        },
                    )
            except Exception:
                pass

        return res

    def watch_outputs(
        self,
        *,
        output_dirs: List[Union[str, Path]],
        interval_sec: float = 10.0,
        patterns: Optional[List[str]] = None,
        stable_required: int = 2,
        min_age_sec: float = 1.0,
        mode: str = "rolling",
        log_snapshot_interval_sec: float = 60.0,
        state_gc_after_sec: float = 7 * 24 * 3600,
    ) -> None:
        if self._outputs_watch_thread and self._outputs_watch_thread.is_alive():
            return
        self._outputs_watch_stop.clear()

        def _loop() -> None:
            while not self._outputs_watch_stop.is_set():
                try:
                    self.scan_outputs_once(
                        output_dirs=output_dirs,
                        patterns=patterns,
                        stable_required=stable_required,
                        min_age_sec=min_age_sec,
                        mode=mode,
                        log_snapshot_interval_sec=log_snapshot_interval_sec,
                        state_gc_after_sec=state_gc_after_sec,
                    )
                except Exception:
                    pass
                self._outputs_watch_stop.wait(interval_sec)

        t = threading.Thread(target=_loop, daemon=True)
        self._outputs_watch_thread = t
        t.start()

    def stop_outputs_watch(self) -> None:
        self._outputs_watch_stop.set()
        t = self._outputs_watch_thread
        if t and t.is_alive():
            t.join(timeout=2.0)

    def _init_modern_storage(self) -> None:
        """Initialize modern storage backend."""
        try:
            # Initialize SQLite backend
            self.storage_backend = SQLiteStorageBackend(self.storage_root)
            
            # Auto-migrate legacy index database if present
            try:
                from .storage.migration import migrate_index_to_unified
                migrate_index_to_unified(self.storage_root, self.storage_backend)
            except Exception as e:
                logger.debug(f"Index migration skipped or failed: {e}")
            
            # Create experiment record in modern storage
            experiment = ExperimentRecord(
                id=self.id,
                path=self.path,
                alias=self.alias,
                created_at=_now_ts(),
                updated_at=_now_ts(),
                status="running",
                pid=os.getpid(),
                python_version=sys.version.split(" ")[0],
                platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
                hostname=socket.gethostname(),
                run_dir=str(self.run_dir),
                workspace_root=str(self.workspace_root),
            )
            
            self.storage_backend.create_experiment(experiment)
            
            logger.info(f"Modern storage initialized: {type(self.storage_backend).__name__}")
            
        except Exception as e:
            logger.error(f"Failed to initialize modern storage: {e}")
            self.storage_backend = None
            raise

    # ---------------- public API -----------------
    def set_primary_metric(self, metric_name: str, mode: str = "max") -> None:
        """Set the primary metric to track for best value display.
        
        Args:
            metric_name: Name of the metric to track (e.g., "accuracy", "loss")
            mode: Optimization direction, either "max" or "min"
        """
        if self._finished:
            logger.warning("set_primary_metric called after finish(); ignoring")
            return
        if mode not in ["max", "min"]:
            raise ValueError(f"Mode must be 'max' or 'min', got '{mode}'")
        
        self._primary_metric_name = metric_name
        self._primary_metric_mode = mode
        self._best_metric_value = None  # Reset when changing metric
        self._best_metric_step = None
        
        logger.info(f"Set primary metric: {metric_name} (mode: {mode})")
    
    def log(self, data: Optional[Dict[str, Any]] = None, *, step: Optional[int] = None, stage: Optional[Any] = None, **kwargs: Any) -> None:
        """Log arbitrary scalar metrics.

        Usage:
            rn.log({"loss": 0.1, "acc": 98.1}, step=10, stage="train")

        Behavior:
        - Maintains a global step counter. If 'step' is provided in a call,
          the counter is set to that value for this record; otherwise it auto-increments.
        - Always records 'global_step' and 'time' into the event data.
        - If 'stage' is provided (or present in data), records it for UI separators.
        """
        if self._finished:
            logger.warning("Run already finished, ignoring %s call", "log")
            return
        ts = _now_ts()
        payload: Dict[str, Any] = {}
        if data:
            payload.update(data)
        if kwargs:
            payload.update(kwargs)

        # Normalize and prioritize explicit params over payload
        # Remove any user-provided 'step' keys to avoid ambiguity; we always store 'global_step'
        payload.pop("global_step", None)
        payload.pop("step", None)

        # Determine step value
        if step is not None:
            try:
                self._global_step = int(step)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid step value '{step}': {e}, auto-incrementing instead")
                self._global_step += 1
        else:
            self._global_step += 1

        # Determine stage value (explicit arg has priority)
        stage_in_payload = payload.pop("stage", None)
        stage_val = stage if stage is not None else stage_in_payload

        # Inject normalized tracking fields
        payload["global_step"] = self._global_step
        payload["time"] = ts
        if stage_val is not None:
            payload["stage"] = stage_val

        # Write to traditional events.jsonl (always for compatibility)
        evt = {"ts": ts, "type": "metrics", "data": payload}
        self._append_jsonl(self._events_path, evt, self._events_lock)
        
        # Also write to modern storage if available
        if self.storage_backend:
            try:
                # Convert metrics to MetricRecord format
                metrics = []
                for metric_name, metric_value in payload.items():
                    if metric_name in ("global_step", "time", "stage"):
                        continue
                    if isinstance(metric_value, (int, float)):
                        metrics.append(MetricRecord(
                            experiment_id=self.id,
                            timestamp=ts,
                            metric_name=metric_name,
                            metric_value=metric_value,
                            step=self._global_step,
                            stage=stage_val
                        ))
                
                if metrics:
                    self.storage_backend.log_metrics(self.id, metrics)
                        
            except Exception as e:
                logger.debug(f"Failed to log to modern storage: {e}")
        
        # Update primary metric best value if configured
        self._update_best_metric(payload)
        
        # Check for anomalies if monitoring is enabled
        if self.monitor:
            try:
                alerts = self.monitor.check_metrics(payload)
                for alert in alerts:
                    self.log_text(alert)
            except Exception as e:
                logger.debug(f"Monitoring check failed: {e}")

    def log_text(self, text: str) -> None:
        if self._finished:
            logger.warning("Run already finished, ignoring %s call", "log_text")
            return
        # Write to logs.txt to support Live Logs viewer
        # Prepend timestamp to each non-empty line; preserve empty lines (BUG-44)
        timestamp = time.strftime("%H:%M:%S")
        lines = text.split("\n")
        prefixed_lines = []
        for line in lines:
            if line.strip():
                prefixed_lines.append(f"{timestamp} | {line}")
            else:
                prefixed_lines.append("")
        formatted_text = "\n".join(prefixed_lines) + "\n"
        with self._logs_lock:
            with open(self._logs_txt_path, "a", encoding="utf-8", errors="ignore") as f:
                f.write(formatted_text)

    def get_logging_handler(
        self,
        level: int = logging.INFO,
        fmt: Optional[str] = None,
    ):
        """
        Get a logging handler that writes to this run's log file.
        
        Usage:
            run = runicorn.init(capture_console=True)
            logger = logging.getLogger(__name__)
            logger.addHandler(run.get_logging_handler())
            logger.info("This goes to logs.txt")
        
        Args:
            level: Minimum log level (default: logging.INFO)
            fmt: Custom format string (optional)
        
        Returns:
            A configured RunicornLoggingHandler instance.
        """
        from .console import RunicornLoggingHandler
        return RunicornLoggingHandler(run=self, level=level, fmt=fmt)

    def log_image(
        self,
        key: str,
        image: Any,
        step: Optional[int] = None,
        caption: Optional[str] = None,
        format: str = "png",
        quality: int = 90,
    ) -> str:
        """Save an image under media/ and record an event.

        Returns the relative path of the saved image.
        """
        if self._finished:
            logger.warning("Run already finished, ignoring %s call", "log_image")
            return ""
        rel_name = f"{int(_now_ts()*1000)}_{uuid.uuid4().hex[:6]}_{key}.{format.lower()}"
        path = self.media_dir / rel_name

        # Accept PIL.Image, numpy array, bytes, path-like
        try:
            if HAS_PIL and hasattr(image, 'save'):  # PIL.Image
                image.save(path, format=format.upper(), quality=quality)
            elif HAS_NUMPY and hasattr(image, "shape"):  # numpy array
                if not HAS_PIL:
                    raise RuntimeError("Pillow is required to save numpy arrays. Install with: pip install pillow")
                img = Image.fromarray(image)
                img.save(path, format=format.upper(), quality=quality)
            elif isinstance(image, (bytes, bytearray)):
                with open(path, "wb") as f:
                    f.write(image)
            else:
                # Try as path-like
                p = Path(str(image))
                if not p.exists():
                    raise FileNotFoundError(f"Image file not found: {image}")
                data = p.read_bytes()
                with open(path, "wb") as f:
                    f.write(data)
        except Exception as e:
            logger.error(f"Failed to save image '{key}': {e}")
            raise

        evt = {
            "ts": _now_ts(),
            "type": "image",
            "data": {"key": key, "path": f"media/{rel_name}", "step": step, "caption": caption},
        }
        self._append_jsonl(self._events_path, evt, self._events_lock)
        return f"media/{rel_name}"

    def log_config(
        self,
        *,
        args: Optional[Any] = None,
        extra: Optional[Dict[str, Any]] = None,
        config_files: Optional[List[Union[str, Path]]] = None,
    ) -> None:
        if self._finished:
            logger.warning("Run already finished, ignoring %s call", "log_config")
            return
        cfg_holder: Dict[str, Any] = {}

        def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
            cfg: Dict[str, Any] = dict((a.get("config") or {}))
            if args is not None:
                raw_args = args if isinstance(args, dict) else vars(args)
                cfg["args"] = _make_json_safe(raw_args)
            if extra is not None:
                cfg["extra"] = _make_json_safe(extra)
            if config_files is not None:
                cfg["config_files"] = [str(Path(p)) for p in config_files]
            a["config"] = cfg
            cfg_holder.clear()
            cfg_holder.update(cfg)
            return a

        update_assets_atomic(self._assets_path, self._assets_lock, _upd)

        if self.storage_backend:
            try:
                self.storage_backend.record_asset_for_run(
                    run_id=self.id,
                    role="config",
                    asset_type="config",
                    name=None,
                    source_uri=None,
                    archive_uri=None,
                    is_archived=False,
                    fingerprint_kind=None,
                    fingerprint=None,
                    created_at=_now_ts(),
                    metadata=cfg_holder,
                )
            except Exception:
                pass

    def log_dataset(
        self,
        name: str,
        root_or_uri: Union[str, Path, Dict[str, Any]],
        *,
        context: str = "train",
        save: bool = False,
        description: Optional[str] = None,
        force_save: bool = False,
        max_archive_bytes: int = 5 * 1024 * 1024 * 1024,
        max_archive_files: int = 2_000_000,
    ) -> None:
        if self._finished:
            logger.warning("log_dataset called after finish(); ignoring")
            return
        uri: Any = root_or_uri
        fp: Optional[Dict[str, Any]] = None
        archived: Optional[Dict[str, Any]] = None

        if isinstance(root_or_uri, (str, Path)):
            p = Path(root_or_uri).expanduser()
            uri = str(p)
            try:
                if p.is_dir():
                    fp = dir_stat_fingerprint(p)
                    if save:
                        if (fp.get("total_size_bytes") or 0) > max_archive_bytes or (fp.get("file_count") or 0) > max_archive_files:
                            if not force_save:
                                raise ValueError("dataset too large to archive; set force_save=True or use save=False")
                        archived = archive_dir(p, self.storage_root / "archive", category="datasets")
                elif p.is_file():
                    fp = stat_fingerprint(p)
                    if save:
                        if (fp.get("size_bytes") or 0) > max_archive_bytes:
                            if not force_save:
                                raise ValueError("dataset file too large to archive; set force_save=True or use save=False")
                        archived = archive_file(p, self.storage_root / "archive", category="datasets")
            except OSError:
                fp = None

        entry: Dict[str, Any] = {
            "name": name,
            "context": context,
            "uri": uri,
            "description": description,
            "saved": bool(save and archived),
            "fingerprint": fp,
        }
        if archived:
            entry.update(archived)

        def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
            a.setdefault("datasets", [])
            a["datasets"].append(entry)
            return a

        update_assets_atomic(self._assets_path, self._assets_lock, _upd)

        if self.storage_backend:
            try:
                fp_kind = entry.get("fingerprint_kind")
                fp_val = entry.get("fingerprint")
                if isinstance(fp_val, dict):
                    fp_val = json.dumps(fp_val, ensure_ascii=False, sort_keys=True)
                    fp_kind = fp_kind or "stat"
                self.storage_backend.record_asset_for_run(
                    run_id=self.id,
                    role="dataset",
                    asset_type="dataset",
                    name=name,
                    source_uri=str(entry.get("uri")) if entry.get("uri") is not None else None,
                    archive_uri=entry.get("archive_path"),
                    is_archived=bool(entry.get("saved")),
                    fingerprint_kind=fp_kind,
                    fingerprint=fp_val,
                    created_at=_now_ts(),
                    metadata={
                        "context": context,
                        "description": description,
                    },
                )
            except Exception:
                pass

    def log_pretrained(
        self,
        name: str,
        *,
        path_or_uri: Optional[Union[str, Path, Dict[str, Any]]] = None,
        save: bool = False,
        source_type: str = "unknown",
        description: Optional[str] = None,
        force_save: bool = False,
        max_archive_bytes: int = 5 * 1024 * 1024 * 1024,
        max_archive_files: int = 2_000_000,
    ) -> None:
        if self._finished:
            logger.warning("log_pretrained called after finish(); ignoring")
            return
        archived: Optional[Dict[str, Any]] = None

        if save and path_or_uri is None:
            raise ValueError("save=True requires path_or_uri")

        if save and isinstance(path_or_uri, (str, Path)):
            p = Path(path_or_uri).expanduser()
            if p.is_dir():
                fp = dir_stat_fingerprint(p)
                if (fp.get("total_size_bytes") or 0) > max_archive_bytes or (fp.get("file_count") or 0) > max_archive_files:
                    if not force_save:
                        raise ValueError("pretrained dir too large to archive; set force_save=True or use save=False")
                archived = archive_dir(p, self.storage_root / "archive", category="pretrained")
            elif p.is_file():
                fp2 = stat_fingerprint(p)
                if (fp2.get("size_bytes") or 0) > max_archive_bytes:
                    if not force_save:
                        raise ValueError("pretrained file too large to archive; set force_save=True or use save=False")
                archived = archive_file(p, self.storage_root / "archive", category="pretrained")

        entry: Dict[str, Any] = {
            "name": name,
            "source_type": source_type,
            "path_or_uri": None if path_or_uri is None else (str(path_or_uri) if isinstance(path_or_uri, (str, Path)) else path_or_uri),
            "description": description,
            "saved": bool(save and archived),
        }
        if archived:
            entry.update(archived)

        def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
            a.setdefault("pretrained", [])
            a["pretrained"].append(entry)
            return a

        update_assets_atomic(self._assets_path, self._assets_lock, _upd)

        if self.storage_backend:
            try:
                self.storage_backend.record_asset_for_run(
                    run_id=self.id,
                    role="pretrained",
                    asset_type="pretrained",
                    name=name,
                    source_uri=str(entry.get("path_or_uri")) if entry.get("path_or_uri") is not None else None,
                    archive_uri=entry.get("archive_path"),
                    is_archived=bool(entry.get("saved")),
                    fingerprint_kind=entry.get("fingerprint_kind"),
                    fingerprint=entry.get("fingerprint"),
                    created_at=_now_ts(),
                    metadata={
                        "source_type": source_type,
                        "description": description,
                    },
                )
            except Exception:
                pass

    def _apply_summary_update(self, update: Dict[str, Any]) -> None:
        """Internal: apply summary update without _finished check (used by finish())."""
        with self._summary_lock:
            cur: Dict[str, Any] = {}
            if self._summary_path.exists():
                try:
                    cur = json.loads(self._summary_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to read summary file: {e}, starting fresh")
                    cur = {}
            cur.update(update or {})
            self._summary_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")

        if self.storage_backend:
            try:
                storage_updates = {}
                if "best_metric_value" in update:
                    storage_updates["best_metric_value"] = update["best_metric_value"]
                if "best_metric_name" in update:
                    storage_updates["best_metric_name"] = update["best_metric_name"]
                if "best_metric_step" in update:
                    storage_updates["best_metric_step"] = update["best_metric_step"]
                if "best_metric_mode" in update:
                    storage_updates["best_metric_mode"] = update["best_metric_mode"]
                if storage_updates:
                    self.storage_backend.update_experiment(self.id, storage_updates)
            except Exception as e:
                logger.debug(f"Failed to update summary in modern storage: {e}")

    def summary(self, update: Dict[str, Any]) -> None:
        if self._finished:
            logger.warning("Run already finished, ignoring %s call", "summary")
            return
        self._apply_summary_update(update)

    def _update_best_metric(self, payload: Dict[str, Any]) -> None:
        """Update the best metric value if primary metric is configured."""
        if not self._primary_metric_name or self._primary_metric_name not in payload:
            return
        
        current_value = payload[self._primary_metric_name]
        if not isinstance(current_value, (int, float)):
            return
        
        # Check if this is a new best value
        is_new_best = False
        if self._best_metric_value is None:
            is_new_best = True
        elif self._primary_metric_mode == "max" and current_value > self._best_metric_value:
            is_new_best = True
        elif self._primary_metric_mode == "min" and current_value < self._best_metric_value:
            is_new_best = True
        
        if is_new_best:
            self._best_metric_value = current_value
            self._best_metric_step = payload.get("global_step", payload.get("step"))
            logger.debug(f"New best {self._primary_metric_name}: {current_value} at step {self._best_metric_step}")
            
            # Update modern storage with new best metric
            if self.storage_backend:
                try:
                    updates = {
                        "best_metric_value": self._best_metric_value,
                        "best_metric_name": self._primary_metric_name,
                        "best_metric_step": self._best_metric_step,
                        "best_metric_mode": self._primary_metric_mode
                    }
                    self.storage_backend.update_experiment(self.id, updates)
                except Exception as e:
                    logger.debug(f"Failed to update best metric in modern storage: {e}")
    
    def finish(self, status: str = "finished") -> None:
        """Mark the run as finished and ensure all data is written."""
        # Normalize status to valid SQLite values (avoids file/SQLite state tear)
        status = _normalize_status(status)

        # Block further writes immediately (BUG-36) - before any cleanup
        self._finished = True
        self._outputs_watch_stop.set()

        # Stop console capture before finishing
        if self._console_capture is not None:
            try:
                self._console_capture.stop()
                logger.debug(f"Console capture stopped for run {self.id}")
            except Exception as e:
                logger.debug(f"Failed to stop console capture: {e}")
            self._console_capture = None

        self.stop_outputs_watch()

        # Save best metric to summary (use internal method since _finished is already True)
        if self._best_metric_value is not None:
            best_metric_summary = {
                "best_metric_value": self._best_metric_value,
                "best_metric_name": self._primary_metric_name,
                "best_metric_step": self._best_metric_step,
                "best_metric_mode": self._primary_metric_mode
            }
            self._apply_summary_update(best_metric_summary)

        # Update status file (always for compatibility)
        with self._status_lock:
            cur: Dict[str, Any] = {}
            if self._status_path.exists():
                try:
                    cur = json.loads(self._status_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to read status file: {e}, starting fresh")
                    cur = {}
            cur.update({"status": status, "ended_at": _now_ts()})
            self._status_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Also update modern storage if available
        if self.storage_backend:
            try:
                updates = {
                    "status": status,
                    "ended_at": _now_ts()
                }
                
                self.storage_backend.update_experiment(self.id, updates)
                    
            except Exception as e:
                logger.debug(f"Failed to update status in modern storage: {e}")
            
            # Close storage backend connections (critical for Windows)
            try:
                if hasattr(self.storage_backend, 'close'):
                    self.storage_backend.close()
                    self.storage_backend = None
                    logger.debug("Closed storage backend connections")
                    
                    # Additional: Force close all file handles
                    import gc
                    gc.collect()  # Force garbage collection to release handles
                    
                    # Small delay for Windows to release file locks
                    import time as time_module
                    time_module.sleep(0.05)
                    
            except Exception as e:
                logger.debug(f"Failed to close storage backend: {e}")
        
        # Force flush to ensure data is written to disk
        try:
            import os
            os.sync()  # Unix/Linux
        except (AttributeError, OSError):
            try:
                import ctypes
                # Windows fallback
                kernel32 = ctypes.windll.kernel32
                kernel32.FlushFileBuffers.argtypes = [ctypes.c_void_p]
                kernel32.FlushFileBuffers.restype = ctypes.c_bool
            except:
                pass  # Best effort
                
        # Small delay to ensure file system catches up
        import time
        time.sleep(0.1)

        # Clear _active_run so get_active_run() does not return a finished run (BUG-36)
        global _active_run
        with _active_run_lock:
            if _active_run is self:
                _active_run = None

    # ---------------- context manager -----------------
    def __enter__(self) -> "Run":
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, finishing the run."""
        status = "failed" if exc_type is not None else "finished"
        self.finish(status=status)

    # ---------------- helpers -----------------
    @staticmethod
    def _write_json(path: Path, obj: Dict[str, Any]) -> None:
        os.makedirs(path.parent, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    
    @staticmethod
    def _append_jsonl(path: Path, obj: Dict[str, Any], lock: FileLock) -> None:
        os.makedirs(path.parent, exist_ok=True)
        with lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# --------------- module-level API ---------------

def init(
    path: Optional[str] = None,
    storage: Optional[str] = None,
    run_id: Optional[str] = None,
    alias: Optional[str] = None,
    capture_env: bool = False,
    snapshot_code: bool = False,
    workspace_root: Optional[str] = None,
    snapshot_format: str = "zip",
    force_snapshot: bool = False,
    capture_console: bool = False,
    tqdm_mode: str = "smart",
) -> Union[Run, NoOpRun]:
    """
    Initialize a new experiment run.
    
    Args:
        path: Experiment path (e.g., "cv/detection/yolo"). Defaults to "default".
        storage: Storage directory path (optional, uses config if not specified)
        run_id: Run ID (optional, auto-generated if not specified)
        alias: Optional user-friendly alias for this run
        capture_env: Whether to capture environment information
        snapshot_code: Whether to snapshot the workspace code
        workspace_root: Workspace root directory for code snapshot
        snapshot_format: Format for code snapshot (currently only "zip")
        force_snapshot: Force snapshot even if workspace is large
        capture_console: Whether to capture stdout/stderr to logs.txt (default: False)
        tqdm_mode: How to handle tqdm progress bars: "smart" (default), "all", or "none"
        
    Returns:
        Run object for logging metrics and managing the experiment
        
    Example:
        >>> import runicorn as rn
        >>> run = rn.init(path="cv/yolo/ablation", alias="best-v2")
        >>> run.log({"loss": 0.5}, step=0)
        >>> run.finish()
        
        # With console capture:
        >>> run = rn.init(path="train", capture_console=True)
        >>> print("This goes to logs.txt")
        >>> run.finish()
    """
    global _active_run
    with _active_run_lock:
        if not is_enabled():
            _active_run = None
            return NoOpRun(path=path, alias=alias)
        r = Run(
            path=path,
            storage=storage,
            run_id=run_id,
            alias=alias,
            capture_env=capture_env,
            snapshot_code=snapshot_code,
            workspace_root=workspace_root,
            snapshot_format=snapshot_format,
            force_snapshot=force_snapshot,
            capture_console=capture_console,
            tqdm_mode=tqdm_mode,
        )
        _active_run = r
    return r
