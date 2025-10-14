from __future__ import annotations

import json
import logging
import os
import platform
import socket
import sys
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union

from filelock import FileLock
from .config import get_user_root_dir

# Setup logging
logger = logging.getLogger(__name__)

# Import modern storage components (graceful fallback if not available)
try:
    from .storage.backends import SQLiteStorageBackend, HybridStorageBackend
    from .storage.models import ExperimentRecord, MetricRecord
    from .storage.migration import ensure_modern_storage, detect_storage_type
    HAS_MODERN_STORAGE = True
    logger.info("Modern storage system available")
except ImportError as e:
    logger.debug(f"Modern storage not available: {e}")
    HAS_MODERN_STORAGE = False

# Optional: Import monitoring if needed
try:
    from .monitors import MetricMonitor, AnomalyDetector
    HAS_MONITORING = True
except ImportError:
    MetricMonitor = None
    AnomalyDetector = None
    HAS_MONITORING = False

# Optional: Import environment capture
try:
    from .environment import EnvironmentCapture
    HAS_ENV_CAPTURE = True
except ImportError:
    EnvironmentCapture = None
    HAS_ENV_CAPTURE = False

# Optional: Import artifacts system
try:
    from .artifacts import Artifact, ArtifactStorage, LineageTracker, create_artifact_storage
    HAS_ARTIFACTS = True
    logger.info("Artifacts system available")
except ImportError as e:
    logger.debug(f"Artifacts system not available: {e}")
    Artifact = None
    ArtifactStorage = None
    LineageTracker = None
    HAS_ARTIFACTS = False

# Optional imports for image handling
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


@dataclass
class RunMeta:
    id: str
    project: str
    name: Optional[str]
    created_at: float
    python: str
    platform: str
    hostname: str
    pid: int
    storage_dir: str


class Run:
    def __init__(
        self,
        project: str = "default",
        storage: Optional[str] = None,
        run_id: Optional[str] = None,
        name: Optional[str] = None,
        capture_env: bool = True,
    ) -> None:
        self.project = project or "default"
        # storage_root points to user_root_dir (or legacy ./.runicorn)
        self.storage_root = _default_storage_dir(storage)
        # New hierarchy: user_root_dir / project / name / runs / run_id
        exp_name = name or "default"
        self.name = exp_name
        self.project_dir = self.storage_root / self.project
        self.experiment_dir = self.project_dir / exp_name
        self.runs_dir = self.experiment_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.id = run_id or _gen_run_id()
        self.run_dir = self.runs_dir / self.id
        self.media_dir = self.run_dir / "media"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)

        self._events_path = self.run_dir / "events.jsonl"
        self._summary_path = self.run_dir / "summary.json"
        self._status_path = self.run_dir / "status.json"
        self._meta_path = self.run_dir / "meta.json"
        self._logs_txt_path = self.run_dir / "logs.txt"  # for websocket tailing

        # Separate locks for files
        self._events_lock = FileLock(str(self._events_path) + ".lock")
        self._summary_lock = FileLock(str(self._summary_path) + ".lock")
        self._status_lock = FileLock(str(self._status_path) + ".lock")
        self._logs_lock = FileLock(str(self._logs_txt_path) + ".lock")

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
        
        # Optional artifacts
        self.artifact_storage = None
        if HAS_ARTIFACTS:
            try:
                self.artifact_storage = create_artifact_storage(self.storage_root)
            except Exception as e:
                logger.warning(f"Failed to initialize artifact storage: {e}")

        meta = RunMeta(
            id=self.id,
            project=self.project,
            name=self.name,
            created_at=_now_ts(),
            python=sys.version.split(" ")[0],
            platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
            hostname=socket.gethostname(),
            pid=os.getpid(),
            storage_dir=str(self.storage_root),
        )
        self._write_json(self._meta_path, asdict(meta))
        self._write_json(self._status_path, {"status": "running", "started_at": _now_ts()})
        
        # Capture environment if requested
        if capture_env and HAS_ENV_CAPTURE:
            try:
                env_capture = EnvironmentCapture()
                env_info = env_capture.capture_all()
                env_info.save(self.run_dir / "environment.json")
                logger.info(f"Environment captured for run {self.id}")
            except Exception as e:
                logger.warning(f"Failed to capture environment: {e}")

    def _init_modern_storage(self) -> None:
        """Initialize modern storage backend."""
        try:
            # Initialize SQLite backend
            self.storage_backend = SQLiteStorageBackend(self.storage_root)
            
            # Create experiment record in modern storage
            experiment = ExperimentRecord(
                id=self.id,
                project=self.project,
                name=self.name,
                created_at=_now_ts(),
                updated_at=_now_ts(),
                status="running",
                pid=os.getpid(),
                python_version=sys.version.split(" ")[0],
                platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
                hostname=socket.gethostname(),
                run_dir=str(self.run_dir)
            )
            
            # Use synchronous wrapper to safely create experiment
            from .storage.sync_utils import create_experiment_sync
            create_experiment_sync(self.storage_backend, experiment)
            
            logger.info(f"✅ Modern storage initialized: {type(self.storage_backend).__name__}")
            
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
                    # Use synchronous wrapper to safely log metrics
                    from .storage.sync_utils import log_metrics_sync
                    log_metrics_sync(self.storage_backend, self.id, metrics)
                        
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
        # Write to logs.txt to support Live Logs viewer
        line = f"{time.strftime('%H:%M:%S')} | {text}\n"
        with self._logs_lock:
            with open(self._logs_txt_path, "a", encoding="utf-8", errors="ignore") as f:
                f.write(line)

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

    def summary(self, update: Dict[str, Any]) -> None:
        # Update traditional summary.json file (always for compatibility)
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
        
        # Also update modern storage if available
        if self.storage_backend:
            try:
                import asyncio
                # Map summary fields to experiment record fields
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
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self.storage_backend.update_experiment(self.id, storage_updates))
                        else:
                            loop.run_until_complete(self.storage_backend.update_experiment(self.id, storage_updates))
                    except RuntimeError:
                        asyncio.run(self.storage_backend.update_experiment(self.id, storage_updates))
                        
            except Exception as e:
                logger.debug(f"Failed to update summary in modern storage: {e}")

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
                    import asyncio
                    updates = {
                        "best_metric_value": self._best_metric_value,
                        "best_metric_name": self._primary_metric_name,
                        "best_metric_step": self._best_metric_step,
                        "best_metric_mode": self._primary_metric_mode
                    }
                    
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self.storage_backend.update_experiment(self.id, updates))
                        else:
                            loop.run_until_complete(self.storage_backend.update_experiment(self.id, updates))
                    except RuntimeError:
                        asyncio.run(self.storage_backend.update_experiment(self.id, updates))
                        
                except Exception as e:
                    logger.debug(f"Failed to update best metric in modern storage: {e}")
    
    def log_artifact(self, artifact: 'Artifact') -> int:
        """
        Log (save) an artifact with version control.
        
        Args:
            artifact: Artifact object to log
            
        Returns:
            Version number assigned to this artifact
            
        Raises:
            RuntimeError: If artifacts system is not available
            
        Example:
            artifact = rn.Artifact("my-model", type="model")
            artifact.add_file("model.pth")
            artifact.add_metadata({"accuracy": 0.95})
            version = run.log_artifact(artifact)
        """
        if not HAS_ARTIFACTS or not self.artifact_storage:
            raise RuntimeError(
                "Artifacts system is not available. "
                "Make sure runicorn.artifacts module is properly installed."
            )
        
        # Save artifact
        version = self.artifact_storage.save_artifact(
            artifact=artifact,
            run_id=self.id,
            staged_files=artifact._staged_files,
            staged_references=artifact._staged_references,
            user=None  # TODO: Add user tracking
        )
        
        # Update artifact object
        artifact._version = version
        artifact._storage = self.artifact_storage
        artifact._is_loaded = True
        
        # Record artifact creation in run metadata
        artifacts_created_path = self.run_dir / "artifacts_created.json"
        
        try:
            if artifacts_created_path.exists():
                try:
                    created = json.loads(artifacts_created_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to read artifacts_created.json, starting fresh: {e}")
                    created = {"artifacts": []}
            else:
                created = {"artifacts": []}
            
            # Calculate size safely (files may have been moved/deleted)
            total_size = 0
            for source_path, _ in artifact._staged_files:
                try:
                    if source_path.exists():
                        total_size += source_path.stat().st_size
                except Exception:
                    pass  # File may have been deleted after staging
            
            created["artifacts"].append({
                "name": artifact.name,
                "type": artifact.type,
                "version": version,
                "created_at": time.time(),
                "size_bytes": total_size,
                "num_files": len(artifact._staged_files),
                "num_references": len(artifact._staged_references)
            })
            
            # Atomic write
            self._write_json_atomic(artifacts_created_path, created)
            
        except Exception as e:
            logger.warning(f"Failed to record artifact creation: {e}")
            # Don't fail the whole operation if recording fails
        
        logger.info(f"Logged artifact {artifact.name}:v{version}")
        return version
    
    def use_artifact(self, artifact_spec: str) -> 'Artifact':
        """
        Use (load) an artifact by name and version.
        
        Args:
            artifact_spec: Artifact specification in format "name:version" or "name:alias"
                         Examples: "my-model:v3", "my-model:latest", "dataset:production"
            
        Returns:
            Artifact object with loaded metadata
            
        Raises:
            RuntimeError: If artifacts system is not available
            FileNotFoundError: If artifact not found
            ValueError: If artifact_spec format is invalid
            
        Example:
            artifact = run.use_artifact("my-model:latest")
            model_path = artifact.download()
        """
        if not HAS_ARTIFACTS or not self.artifact_storage:
            raise RuntimeError(
                "Artifacts system is not available. "
                "Make sure runicorn.artifacts module is properly installed."
            )
        
        # Parse artifact spec
        if ":" not in artifact_spec:
            raise ValueError(
                f"Artifact spec must be in format 'name:version' or 'name:alias', got: {artifact_spec}"
            )
        
        name, version_or_alias = artifact_spec.split(":", 1)
        
        # Determine type by searching
        artifact_type = None
        for type_name in ["model", "dataset", "config", "code", "custom"]:
            artifact_dir = self.artifact_storage.artifacts_root / type_name / name
            if artifact_dir.exists():
                artifact_type = type_name
                break
        
        if not artifact_type:
            raise FileNotFoundError(f"Artifact not found: {name}")
        
        # Determine version number
        if version_or_alias.lower().startswith("v"):
            # Direct version number (case-insensitive)
            try:
                version = int(version_or_alias[1:])
                if version <= 0:
                    raise ValueError(f"Invalid version number: {version}")
            except (ValueError, IndexError) as e:
                raise ValueError(f"Invalid version format: {version_or_alias}") from e
        else:
            # Alias (e.g., "latest", "production")
            index = self.artifact_storage._load_index(name, artifact_type)
            version = index.get_version_by_alias(version_or_alias)
            
            if version is None:
                available_aliases = list(index.aliases.keys())
                raise ValueError(
                    f"Alias not found: {version_or_alias} for artifact {name}. "
                    f"Available aliases: {available_aliases}"
                )
        
        # Load artifact
        metadata, manifest = self.artifact_storage.load_artifact(name, artifact_type, version)
        
        # Create artifact object
        artifact = Artifact(
            name=name,
            type=artifact_type,
            description=metadata.description,
            metadata=metadata.metadata
        )
        artifact._version = version
        artifact._storage = self.artifact_storage
        artifact._manifest = manifest
        artifact._artifact_metadata = metadata
        artifact._is_loaded = True
        
        # Record artifact usage in run metadata
        artifacts_used_path = self.run_dir / "artifacts_used.json"
        
        try:
            if artifacts_used_path.exists():
                try:
                    used = json.loads(artifacts_used_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to read artifacts_used.json, starting fresh: {e}")
                    used = {"artifacts": []}
            else:
                used = {"artifacts": []}
            
            # Check if already recorded (avoid duplicates)
            already_recorded = any(
                a["name"] == name and a["version"] == version
                for a in used.get("artifacts", [])
            )
            
            if not already_recorded:
                used["artifacts"].append({
                    "name": name,
                    "type": artifact_type,
                    "version": version,
                    "used_at": time.time(),
                    "size_bytes": metadata.size_bytes,
                    "num_files": metadata.num_files
                })
                
                # Atomic write
                self._write_json_atomic(artifacts_used_path, used)
        except Exception as e:
            logger.warning(f"Failed to record artifact usage: {e}")
            # Don't fail the whole operation
        
        logger.info(f"Using artifact {name}:v{version}")
        return artifact
    
    def finish(self, status: str = "finished") -> None:
        """Mark the run as finished and ensure all data is written."""
        # Save best metric to summary before finishing
        if self._best_metric_value is not None:
            best_metric_summary = {
                "best_metric_value": self._best_metric_value,
                "best_metric_name": self._primary_metric_name,
                "best_metric_step": self._best_metric_step,
                "best_metric_mode": self._primary_metric_mode
            }
            self.summary(best_metric_summary)
        
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
                import asyncio
                updates = {
                    "status": status,
                    "ended_at": _now_ts()
                }
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.storage_backend.update_experiment(self.id, updates))
                    else:
                        loop.run_until_complete(self.storage_backend.update_experiment(self.id, updates))
                except RuntimeError:
                    asyncio.run(self.storage_backend.update_experiment(self.id, updates))
                    
            except Exception as e:
                logger.debug(f"Failed to update status in modern storage: {e}")
            
            # Close storage backend connections (critical for Windows)
            try:
                if hasattr(self.storage_backend, 'close'):
                    self.storage_backend.close()
                    logger.debug("Closed storage backend connections")
                    
                    # Additional: Force close all file handles
                    import gc
                    gc.collect()  # Force garbage collection to release handles
                    
                    # Small delay for Windows to release file locks
                    import time as time_module
                    time_module.sleep(0.05)
                    
            except Exception as e:
                logger.debug(f"Failed to close storage backend: {e}")
        
        # Close artifact storage (if initialized)
        if self.artifact_storage and hasattr(self.artifact_storage, 'close'):
            try:
                # ArtifactStorage doesn't have close, but check anyway
                pass
            except Exception:
                pass
            
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

    # ---------------- helpers -----------------
    @staticmethod
    def _write_json(path: Path, obj: Dict[str, Any]) -> None:
        os.makedirs(path.parent, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    
    @staticmethod
    def _write_json_atomic(path: Path, obj: Dict[str, Any]) -> None:
        """
        Write JSON file atomically using temp-then-rename pattern.
        
        This prevents corruption if process crashes during write.
        Windows-compatible version.
        """
        os.makedirs(path.parent, exist_ok=True)
        
        import tempfile
        
        # Create temp file (Windows: must close fd before using path)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".json.tmp",
            text=False  # Binary mode for Windows
        )
        
        try:
            # Close fd immediately (Windows compatibility)
            os.close(temp_fd)
            
            # Write to temp file
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            
            # On Windows, must remove target first
            if os.name == 'nt' and path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass
            
            # Atomic rename
            Path(temp_path).replace(path)
            
        except Exception:
            # Clean up temp file
            try:
                if Path(temp_path).exists():
                    Path(temp_path).unlink()
            except Exception:
                pass
            raise
 
    @staticmethod
    def _append_jsonl(path: Path, obj: Dict[str, Any], lock: FileLock) -> None:
        os.makedirs(path.parent, exist_ok=True)
        with lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# --------------- module-level convenience APIs ---------------

def init(project: str = "default", storage: Optional[str] = None, run_id: Optional[str] = None, name: Optional[str] = None, capture_env: bool = True) -> Run:
    global _active_run
    with _active_run_lock:
        r = Run(project=project, storage=storage, run_id=run_id, name=name, capture_env=capture_env)
        _active_run = r
    return r


def _require_run() -> Run:
    r = get_active_run()
    if r is None:
        raise RuntimeError("runicorn.init() must be called before logging")
    return r


def log(data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
    # Support rn.log({...}, step=..., stage=..., key=value...)
    # Pull out recognized kwargs to keep type hints simple at module level
    step = kwargs.pop("step", None)
    stage = kwargs.pop("stage", None)
    _require_run().log(data, step=step, stage=stage, **kwargs)


def log_text(text: str) -> None:
    """
    Log text message to the logs file.
    
    This provides a consistent module-level API for text logging,
    matching the pattern of other module-level functions like log().
    
    Args:
        text: Text message to log
    """
    _require_run().log_text(text)


def log_image(key: str, image: Any, step: Optional[int] = None, caption: Optional[str] = None, format: str = "png", quality: int = 90) -> str:
    return _require_run().log_image(key=key, image=image, step=step, caption=caption, format=format, quality=quality)


def summary(update: Dict[str, Any]) -> None:
    _require_run().summary(update)


def finish(status: str = "finished") -> None:
    _require_run().finish(status)


def set_primary_metric(metric_name: str, mode: str = "max") -> None:
    """Set the primary metric to track for best value display.
    
    Args:
        metric_name: Name of the metric to track (e.g., "accuracy", "loss")
        mode: Optimization direction, either "max" or "min"
    """
    _require_run().set_primary_metric(metric_name, mode)
