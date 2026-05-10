"""
Diagnostics logging helpers for local and remote viewer sessions.
"""
from __future__ import annotations

import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

LOCAL_LOG_ROOT = Path.home() / ".runicorn" / "logs"
LOCAL_SESSION_LOG_DIR = LOCAL_LOG_ROOT / "sessions"
REMOTE_LOG_ROOT = Path("/tmp/runicorn-viewer")
REMOTE_SESSION_LOG_DIR = REMOTE_LOG_ROOT / "sessions"

MAX_SESSION_HISTORY = 20
MAX_SESSION_AGE_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class DiagnosticsLogContext:
    app_session_id: str
    remote_mode: bool
    global_log_path: Optional[Path]
    session_log_path: Path
    sources: Dict[str, Path]
    session_dir: Path


def _generate_session_id(prefix: str) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    return f"{prefix}-{ts}-{os.getpid()}-{uuid.uuid4().hex[:6]}"


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _remove_path(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    except OSError:
        pass


def _prune_entries(
    entries: Iterable[Path],
    *,
    keep: int = MAX_SESSION_HISTORY,
    max_age_seconds: int = MAX_SESSION_AGE_SECONDS,
    exclude: Optional[Path] = None,
) -> None:
    now = time.time()
    filtered = []
    for entry in entries:
        if exclude is not None and entry == exclude:
            continue
        if not entry.exists():
            continue
        filtered.append(entry)

    # Age-based pruning first.
    for entry in list(filtered):
        if now - _safe_mtime(entry) > max_age_seconds:
            _remove_path(entry)
            filtered.remove(entry)

    # Then keep the most recent N items.
    filtered.sort(key=_safe_mtime, reverse=True)
    for entry in filtered[keep:]:
        _remove_path(entry)


def _build_local_context() -> DiagnosticsLogContext:
    LOCAL_LOG_ROOT.mkdir(parents=True, exist_ok=True)
    LOCAL_SESSION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    _prune_entries(LOCAL_SESSION_LOG_DIR.glob("*.log"))

    app_session_id = _generate_session_id("app")
    global_log_path = LOCAL_LOG_ROOT / "viewer.log"
    session_log_path = LOCAL_SESSION_LOG_DIR / f"{app_session_id}.log"
    return DiagnosticsLogContext(
        app_session_id=app_session_id,
        remote_mode=False,
        global_log_path=global_log_path,
        session_log_path=session_log_path,
        sources={
            "session": session_log_path,
            "global": global_log_path,
        },
        session_dir=LOCAL_SESSION_LOG_DIR,
    )


def _build_remote_context() -> DiagnosticsLogContext:
    remote_session_id = os.environ.get("RUNICORN_REMOTE_SESSION_ID") or _generate_session_id("remote")
    remote_log_root = Path(os.environ.get("RUNICORN_REMOTE_LOG_ROOT") or REMOTE_LOG_ROOT)
    session_dir = Path(os.environ.get("RUNICORN_REMOTE_LOG_DIR") or (remote_log_root / "sessions" / remote_session_id))
    session_dir.mkdir(parents=True, exist_ok=True)
    _prune_entries(session_dir.parent.glob("*"), exclude=session_dir)

    session_log_path = Path(os.environ.get("RUNICORN_LOG_FILE") or (session_dir / "viewer.log"))
    bootstrap_log_path = session_dir / "bootstrap.log"
    return DiagnosticsLogContext(
        app_session_id=remote_session_id,
        remote_mode=True,
        global_log_path=None,
        session_log_path=session_log_path,
        sources={
            "viewer": session_log_path,
            "bootstrap": bootstrap_log_path,
        },
        session_dir=session_dir,
    )


def build_diagnostics_context(remote_mode: bool) -> DiagnosticsLogContext:
    return _build_remote_context() if remote_mode else _build_local_context()


def diagnostics_sources_payload(context: DiagnosticsLogContext) -> list[dict]:
    payload = []
    for source_id, path in context.sources.items():
        payload.append(
            {
                "id": source_id,
                "kind": source_id,
                "path": str(path),
                "available": path.exists(),
            }
        )
    return payload


def resolve_source_path(context: DiagnosticsLogContext, source_id: str) -> Path:
    try:
        return context.sources[source_id]
    except KeyError as e:
        raise KeyError(f"Unknown diagnostics source: {source_id}") from e
