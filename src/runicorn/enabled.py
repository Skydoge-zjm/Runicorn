from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional


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
    def __init__(self, path: Optional[str] = None, alias: Optional[str] = None) -> None:
        self.path = path or "default"
        self.alias = alias
        self.id = "disabled"
        self._assets_manifest: Dict[str, Any] = {}
        self._events: List[Dict[str, Any]] = []
        self._output_watch_stop = False
        self._output_watch_thread: Optional[Any] = None
        self._storage_assets: List[Dict[str, Any]] = []
        self._summary_data: Dict[str, Any] = {}
        self._status_data: Dict[str, Any] = {}
        self._finished = False

    def __enter__(self) -> "NoOpRun":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def get_logging_handler(self) -> logging.Handler:
        return logging.NullHandler()

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
        self.request_output_watch_stop()
        return None

    def append_event(self, event: Dict[str, Any]) -> None:
        self._events.append(dict(event))

    def update_assets_manifest(self, updater) -> None:
        current = dict(self._assets_manifest)
        updated = updater(current)
        if isinstance(updated, dict):
            self._assets_manifest = updated
        else:
            self._assets_manifest = current

    def should_stop_output_watch(self) -> bool:
        return self._finished or self._output_watch_stop

    def clear_output_watch_stop(self) -> None:
        self._output_watch_stop = False

    def request_output_watch_stop(self) -> None:
        self._output_watch_stop = True

    def get_output_watch_thread(self) -> Optional[Any]:
        return self._output_watch_thread

    def set_output_watch_thread(self, thread: Optional[Any]) -> None:
        self._output_watch_thread = thread

    def list_storage_assets(self) -> List[Dict[str, Any]]:
        return [dict(asset) for asset in self._storage_assets]

    def unlink_storage_asset(self, asset_id: str) -> None:
        self._storage_assets = [
            dict(asset)
            for asset in self._storage_assets
            if asset.get("asset_id") != asset_id and asset.get("id") != asset_id
        ]

    def record_storage_asset(self, **kwargs: Any) -> None:
        self._storage_assets.append(dict(kwargs))

    def read_summary_data(self) -> Dict[str, Any]:
        return dict(self._summary_data)

    def write_summary_data(self, data: Dict[str, Any]) -> None:
        self._summary_data = dict(data)

    def read_status_data(self) -> Dict[str, Any]:
        return dict(self._status_data)

    def write_status_data(self, data: Dict[str, Any]) -> None:
        self._status_data = dict(data)

    def close_storage_backend(self) -> None:
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

    def summary(self, update: Dict[str, Any]) -> None:
        return None

    def finish(self, status: str = "finished") -> None:
        self._finished = True
        self.request_output_watch_stop()
        return None
