from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional


_ENABLED_OVERRIDE: Optional[bool] = None


def _parse_bool(s: str) -> Optional[bool]:
    v = (s or "").strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return None


def is_enabled() -> bool:
    if _ENABLED_OVERRIDE is not None:
        return _ENABLED_OVERRIDE
    v = _parse_bool(os.environ.get("RUNICORN_ON", ""))
    if v is None:
        return True
    return v


def set_enabled(enabled: bool) -> None:
    global _ENABLED_OVERRIDE
    _ENABLED_OVERRIDE = bool(enabled)


def reset_enabled() -> None:
    global _ENABLED_OVERRIDE
    _ENABLED_OVERRIDE = None


@contextmanager
def enabled(enabled: bool) -> Iterator[None]:
    global _ENABLED_OVERRIDE
    prev = _ENABLED_OVERRIDE
    try:
        set_enabled(enabled)
        yield
    finally:
        _ENABLED_OVERRIDE = prev


class NoOpRun:
    def __init__(self, project: str = "default", name: Optional[str] = None) -> None:
        self.project = project or "default"
        self.name = name or "default"
        self.id = "disabled"

    def set_primary_metric(self, metric_name: str, mode: str = "max") -> None:
        return None

    def log(self, data: Optional[Dict[str, Any]] = None, *, step: Optional[int] = None, stage: Optional[Any] = None, **kwargs: Any) -> None:
        return None

    def log_text(self, text: str) -> None:
        return None

    def log_image(
        self,
        key: str,
        image: Any,
        step: Optional[int] = None,
        caption: Optional[str] = None,
        format: str = "png",
        quality: int = 90,
    ) -> str:
        return ""

    def log_config(
        self,
        *,
        args: Optional[Any] = None,
        extra: Optional[Dict[str, Any]] = None,
        config_files: Optional[list[Any]] = None,
    ) -> None:
        return None

    def scan_outputs_once(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {"scanned": 0, "archived": 0, "changed": 0}

    def watch_outputs(self, *args: Any, **kwargs: Any) -> None:
        return None

    def stop_outputs_watch(self) -> None:
        return None

    def log_dataset(
        self,
        name: str,
        root_or_uri: Any,
        *,
        context: str = "train",
        save: bool = False,
        description: Optional[str] = None,
        force_save: bool = False,
        max_archive_bytes: int = 0,
        max_archive_files: int = 0,
    ) -> None:
        return None

    def log_pretrained(
        self,
        name: str,
        *,
        path_or_uri: Optional[Any] = None,
        save: bool = False,
        source_type: str = "unknown",
        description: Optional[str] = None,
        force_save: bool = False,
        max_archive_bytes: int = 0,
        max_archive_files: int = 0,
    ) -> None:
        return None

    def log_artifact(self, artifact: Any) -> int:
        return 0

    def use_artifact(self, artifact_spec: str) -> Any:
        return None

    def summary(self, update: Dict[str, Any]) -> None:
        return None

    def finish(self, status: str = "finished") -> None:
        return None
