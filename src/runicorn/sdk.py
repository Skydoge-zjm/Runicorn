from __future__ import annotations

import json
import os
import platform
import socket
import sys
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from filelock import FileLock
from .config import get_user_root_dir

# Optional imports for image handling
try:  # pillow is optional
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore

try:  # numpy is optional
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore


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

    # ---------------- public API -----------------
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
            except Exception:
                # If unparsable, ignore and just auto-increment
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

        evt = {"ts": ts, "type": "metrics", "data": payload}
        self._append_jsonl(self._events_path, evt, self._events_lock)

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
        if Image and isinstance(image, Image.Image):  # type: ignore
            image.save(path, format=format.upper(), quality=quality)
        elif np is not None and hasattr(image, "shape"):
            # Treat as numpy array
            if Image is None:  # pragma: no cover
                raise RuntimeError("Pillow is required to save numpy arrays")
            img = Image.fromarray(image)
            img.save(path, format=format.upper(), quality=quality)
        elif isinstance(image, (bytes, bytearray)):
            with open(path, "wb") as f:
                f.write(image)
        else:
            # Try as path-like
            p = Path(str(image))
            if not p.exists():
                raise FileNotFoundError(f"image not found: {image}")
            data = p.read_bytes()
            with open(path, "wb") as f:
                f.write(data)

        evt = {
            "ts": _now_ts(),
            "type": "image",
            "data": {"key": key, "path": f"media/{rel_name}", "step": step, "caption": caption},
        }
        self._append_jsonl(self._events_path, evt, self._events_lock)
        return f"media/{rel_name}"

    def summary(self, update: Dict[str, Any]) -> None:
        with self._summary_lock:
            cur: Dict[str, Any] = {}
            if self._summary_path.exists():
                try:
                    cur = json.loads(self._summary_path.read_text(encoding="utf-8"))
                except Exception:
                    cur = {}
            cur.update(update or {})
            self._summary_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")

    def finish(self, status: str = "finished") -> None:
        with self._status_lock:
            cur: Dict[str, Any] = {}
            if self._status_path.exists():
                try:
                    cur = json.loads(self._status_path.read_text(encoding="utf-8"))
                except Exception:
                    cur = {}
            cur.update({"status": status, "ended_at": _now_ts()})
            self._status_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")

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


# --------------- module-level convenience APIs ---------------

def init(project: str = "default", storage: Optional[str] = None, run_id: Optional[str] = None, name: Optional[str] = None) -> Run:
    global _active_run
    with _active_run_lock:
        r = Run(project=project, storage=storage, run_id=run_id, name=name)
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


def log_image(key: str, image: Any, step: Optional[int] = None, caption: Optional[str] = None, format: str = "png", quality: int = 90) -> str:
    return _require_run().log_image(key=key, image=image, step=step, caption=caption, format=format, quality=quality)


def summary(update: Dict[str, Any]) -> None:
    _require_run().summary(update)


def finish(status: str = "finished") -> None:
    _require_run().finish(status)
