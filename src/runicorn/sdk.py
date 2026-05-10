from __future__ import annotations

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
from .assets.assets_json import ensure_assets_file, update_assets_atomic
from .assets.archive import archive_dir, archive_file
from .assets.fingerprint import dir_stat_fingerprint, stat_fingerprint
from .assets.snapshot import snapshot_workspace
from .assets.outputs_scan import scan_outputs_once
from ._sdk.run_assets import (
    log_config_impl,
    log_dataset_impl,
    log_pretrained_impl,
    scan_outputs_once_impl,
    stop_outputs_watch_impl,
    watch_outputs_impl,
)
from ._sdk.run_finish import exit_impl, finish_impl
from ._sdk.run_logging import (
    apply_summary_update,
    get_logging_handler as get_run_logging_handler,
    log_image as log_run_image,
    log_metrics,
    log_text as log_run_text,
    set_primary_metric as set_run_primary_metric,
    summary as update_summary,
    update_best_metric,
)

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
        return scan_outputs_once_impl(
            self,
            output_dirs=output_dirs,
            patterns=patterns,
            stable_required=stable_required,
            min_age_sec=min_age_sec,
            mode=mode,
            log_snapshot_interval_sec=log_snapshot_interval_sec,
            state_gc_after_sec=state_gc_after_sec,
            scan_outputs_once_fn=scan_outputs_once,
            logger=logger,
        )

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
        watch_outputs_impl(
            self,
            output_dirs=output_dirs,
            interval_sec=interval_sec,
            patterns=patterns,
            stable_required=stable_required,
            min_age_sec=min_age_sec,
            mode=mode,
            log_snapshot_interval_sec=log_snapshot_interval_sec,
            state_gc_after_sec=state_gc_after_sec,
        )

    def stop_outputs_watch(self) -> None:
        stop_outputs_watch_impl(self)

    @property
    def is_finished(self) -> bool:
        return self._finished

    def append_event(self, event: Dict[str, Any]) -> None:
        self._append_jsonl(self._events_path, event, self._events_lock)

    def update_assets_manifest(self, updater) -> None:
        update_assets_atomic(self._assets_path, self._assets_lock, updater)

    def should_stop_output_watch(self) -> bool:
        return self._finished or self._outputs_watch_stop.is_set()

    def clear_output_watch_stop(self) -> None:
        self._outputs_watch_stop.clear()

    def request_output_watch_stop(self) -> None:
        self._outputs_watch_stop.set()

    def get_output_watch_thread(self) -> Optional[threading.Thread]:
        return self._outputs_watch_thread

    def set_output_watch_thread(self, thread: Optional[threading.Thread]) -> None:
        self._outputs_watch_thread = thread

    def list_storage_assets(self) -> List[Dict[str, Any]]:
        if not self.storage_backend:
            return []
        return self.storage_backend.get_assets_for_run(self.id)

    def unlink_storage_asset(self, asset_id: str) -> None:
        if self.storage_backend and hasattr(self.storage_backend, "unlink_run_asset"):
            self.storage_backend.unlink_run_asset(self.id, asset_id)

    def record_storage_asset(self, **kwargs: Any) -> None:
        if self.storage_backend:
            self.storage_backend.record_asset_for_run(run_id=self.id, **kwargs)

    def read_summary_data(self) -> Dict[str, Any]:
        if not self._summary_path.exists():
            return {}
        try:
            data = json.loads(self._summary_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
        return data if isinstance(data, dict) else {}

    def write_summary_data(self, data: Dict[str, Any]) -> None:
        self._summary_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def read_status_data(self) -> Dict[str, Any]:
        if not self._status_path.exists():
            return {}
        try:
            data = json.loads(self._status_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
        return data if isinstance(data, dict) else {}

    def write_status_data(self, data: Dict[str, Any]) -> None:
        self._status_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def close_storage_backend(self) -> None:
        if self.storage_backend and hasattr(self.storage_backend, "close"):
            self.storage_backend.close()
            self.storage_backend = None

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
        set_run_primary_metric(self, metric_name, mode, logger=logger)
    
    def log(self, data: Optional[Dict[str, Any]] = None, *, step: Optional[int] = None, stage: Optional[Any] = None, **kwargs: Any) -> None:
        log_metrics(
            self,
            data=data,
            step=step,
            stage=stage,
            extra_kwargs=kwargs,
            now_ts=_now_ts,
            metric_record_cls=MetricRecord if HAS_MODERN_STORAGE else None,
            logger=logger,
        )

    def log_text(self, text: str) -> None:
        log_run_text(self, text, logger=logger)

    def get_logging_handler(
        self,
        level: int = logging.INFO,
        fmt: Optional[str] = None,
    ):
        return get_run_logging_handler(self, level=level, fmt=fmt)

    def log_image(
        self,
        key: str,
        image: Any,
        step: Optional[int] = None,
        caption: Optional[str] = None,
        format: str = "png",
        quality: int = 90,
    ) -> str:
        return log_run_image(
            self,
            key=key,
            image=image,
            step=step,
            caption=caption,
            format=format,
            quality=quality,
            now_ts=_now_ts,
            has_pil=HAS_PIL,
            has_numpy=HAS_NUMPY,
            image_module=Image,
            logger=logger,
        )

    def log_config(
        self,
        *,
        args: Optional[Any] = None,
        extra: Optional[Dict[str, Any]] = None,
        config_files: Optional[List[Union[str, Path]]] = None,
    ) -> None:
        log_config_impl(
            self,
            args=args,
            extra=extra,
            config_files=config_files,
            make_json_safe=_make_json_safe,
            now_ts=_now_ts,
            logger=logger,
        )

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
        log_dataset_impl(
            self,
            name=name,
            root_or_uri=root_or_uri,
            context=context,
            save=save,
            description=description,
            force_save=force_save,
            max_archive_bytes=max_archive_bytes,
            max_archive_files=max_archive_files,
            now_ts=_now_ts,
            logger=logger,
        )

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
        log_pretrained_impl(
            self,
            name=name,
            path_or_uri=path_or_uri,
            save=save,
            source_type=source_type,
            description=description,
            force_save=force_save,
            max_archive_bytes=max_archive_bytes,
            max_archive_files=max_archive_files,
            now_ts=_now_ts,
            logger=logger,
        )

    def _apply_summary_update(self, update: Dict[str, Any]) -> None:
        apply_summary_update(self, update, logger=logger)

    def summary(self, update: Dict[str, Any]) -> None:
        update_summary(self, update, logger=logger)

    def _update_best_metric(self, payload: Dict[str, Any]) -> None:
        update_best_metric(self, payload, logger=logger)
    
    def finish(self, status: str = "finished") -> None:
        finish_impl(
            self,
            status=status,
            normalize_status=_normalize_status,
            now_ts=_now_ts,
            active_run_state={
                "lock": _active_run_lock,
                "get": lambda: _active_run,
                "set": lambda value: globals().__setitem__("_active_run", value),
            },
            logger=logger,
        )

    # ---------------- context manager -----------------
    def __enter__(self) -> "Run":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        exit_impl(self, exc_type)

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
