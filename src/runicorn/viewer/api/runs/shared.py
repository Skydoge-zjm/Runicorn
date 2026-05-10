from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List

from fastapi import Request

from ....storage.file_utils import read_json
from ...services.db_reader import get_backend

logger = logging.getLogger(__name__)


def _count_assets_from_assets_json(assets: Any) -> int:
    if not isinstance(assets, dict):
        return 0
    n = 0
    code = assets.get("code")
    if isinstance(code, dict) and isinstance(code.get("snapshot"), dict):
        n += 1
    config = assets.get("config")
    if isinstance(config, dict) and len(config) > 0:
        n += 1
    datasets = assets.get("datasets")
    if isinstance(datasets, list):
        n += len(datasets)
    pretrained = assets.get("pretrained")
    if isinstance(pretrained, list):
        n += len(pretrained)
    outputs = assets.get("outputs")
    if isinstance(outputs, list):
        n += len(outputs)
    return int(n)


def _iter_archive_paths(node: Any):
    if isinstance(node, dict):
        archive_path = node.get("archive_path")
        if isinstance(archive_path, str) and archive_path.strip():
            yield Path(archive_path)
        for value in node.values():
            yield from _iter_archive_paths(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_archive_paths(item)


def _get_allowed_download_roots(run_id: str, request: Request, run_dir: Path) -> List[Path]:
    allowed: List[Path] = [run_dir]
    seen: set[str] = {str(run_dir)}

    def _add(candidate: Any) -> None:
        if not isinstance(candidate, Path):
            return
        key = str(candidate)
        if key in seen:
            return
        seen.add(key)
        allowed.append(candidate)

    backend = get_backend(request)
    if backend is not None:
        try:
            for asset in backend.get_assets_for_run(run_id):
                archive_uri = asset.get("archive_uri")
                if isinstance(archive_uri, str) and archive_uri.strip():
                    _add(Path(archive_uri))
        except Exception:
            pass

    assets_path = run_dir / "assets.json"
    if assets_path.exists():
        assets = read_json(assets_path)
        for archive_path in _iter_archive_paths(assets):
            _add(archive_path)

    return allowed
