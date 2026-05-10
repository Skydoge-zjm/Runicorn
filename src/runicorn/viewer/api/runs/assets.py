from __future__ import annotations

import json
import mimetypes
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ....security.path_validation import validate_resolved_path_against_roots
from ....storage.file_utils import read_json
from ..storage_utils import get_storage_root
from ...services.db_reader import find_run_entry_fast
from ...utils.helpers import is_within_directory
from .shared import _count_assets_from_assets_json, _get_allowed_download_roots, logger

router = APIRouter()


def _read_image_events_from_events_jsonl(run_dir: Path) -> List[Dict[str, Any]]:
    images: List[Dict[str, Any]] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return images
    try:
        with open(events_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    if not isinstance(evt, dict) or evt.get("type") != "image":
                        continue
                    data = evt.get("data")
                    if not isinstance(data, dict):
                        continue
                    rel_path = data.get("path")
                    if not rel_path or not isinstance(rel_path, str):
                        continue
                    abs_path = run_dir / rel_path
                    if not abs_path.exists():
                        continue
                    images.append(
                        {
                            "step": data.get("step"),
                            "key": data.get("key") or "image",
                            "path": str(abs_path),
                        }
                    )
                except (json.JSONDecodeError, TypeError):
                    continue
    except Exception as e:
        logger.debug("Failed to read image events from %s: %s", events_path, e)
    return images


@router.get("/runs/{run_id}/images")
async def get_run_images(run_id: str, request: Request) -> Dict[str, Any]:
    entry = find_run_entry_fast(request, run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    images = _read_image_events_from_events_jsonl(entry.dir)
    return {"run_id": run_id, "images": images}


@router.get("/runs/{run_id}/assets")
async def get_run_assets(run_id: str, request: Request) -> Dict[str, Any]:
    entry = find_run_entry_fast(request, run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")
    run_dir = entry.dir
    assets_path = run_dir / "assets.json"
    assets = read_json(assets_path) if assets_path.exists() else {}
    return {
        "run_id": run_id,
        "assets": assets,
        "assets_count": _count_assets_from_assets_json(assets),
    }


@router.get("/runs/{run_id}/assets/download")
async def download_run_asset(
    run_id: str,
    request: Request,
    path: str = Query(..., description="Absolute file/directory path under storage_root"),
    filename: Optional[str] = Query(None, description="Optional download filename override"),
) -> FileResponse:
    storage_root = get_storage_root(request)
    entry = find_run_entry_fast(request, run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")

    run_dir = entry.dir
    target = Path(path)
    if not is_within_directory(storage_root, target):
        raise HTTPException(status_code=403, detail="Unsafe path")

    allowed_roots = _get_allowed_download_roots(run_id, request, run_dir)
    is_allowed, _ = validate_resolved_path_against_roots(target, allowed_roots)
    if not is_allowed:
        raise HTTPException(status_code=403, detail="Path does not belong to this run")
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    download_name: Optional[str] = None
    if filename is not None:
        name = os.path.basename(filename).replace("\\", "_").replace("/", "_")
        if name.strip():
            download_name = name

    if target.is_file() and target.suffix == ".json" and "manifests" in str(target):
        return await _download_from_manifest(target, storage_root, download_name)
    if target.is_file():
        final_name = download_name or target.name
        media_type, _ = mimetypes.guess_type(final_name)
        return FileResponse(path=str(target), filename=final_name, media_type=media_type or "application/octet-stream")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Unsupported target")

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="runicorn_asset_", suffix=".zip", text=False)
    os.close(tmp_fd)
    tmp_zip = Path(tmp_path)

    def _cleanup() -> None:
        try:
            if tmp_zip.exists():
                tmp_zip.unlink()
        except Exception:
            pass

    try:
        with zipfile.ZipFile(str(tmp_zip), "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _, filenames in os.walk(target):
                dp = Path(dirpath)
                for fn in filenames:
                    fp = dp / fn
                    try:
                        rel = fp.relative_to(target).as_posix()
                    except Exception:
                        rel = fp.name
                    zf.write(str(fp), arcname=rel)
    except Exception:
        _cleanup()
        raise

    final_name = download_name or f"{target.name}.zip"
    if not final_name.lower().endswith(".zip"):
        final_name = f"{final_name}.zip"

    return FileResponse(
        path=str(tmp_zip),
        filename=final_name,
        media_type="application/zip",
        background=BackgroundTask(_cleanup),
    )


async def _download_from_manifest(
    manifest_path: Path,
    storage_root: Path,
    download_name: Optional[str],
) -> FileResponse:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read manifest: {e}")

    files = manifest.get("files", {})
    if not files:
        raise HTTPException(status_code=404, detail="Manifest contains no files")

    blob_root = storage_root / "archive" / "blobs"
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="runicorn_manifest_", suffix=".zip", text=False)
    os.close(tmp_fd)
    tmp_zip = Path(tmp_path)

    def _cleanup() -> None:
        try:
            if tmp_zip.exists():
                tmp_zip.unlink()
        except Exception:
            pass

    try:
        with zipfile.ZipFile(str(tmp_zip), "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rel_path, entry in files.items():
                sha256 = entry.get("sha256")
                if not sha256:
                    continue
                blob_path = blob_root / sha256[:2] / sha256
                if not blob_path.exists():
                    logger.warning("Blob not found: %s for %s", sha256, rel_path)
                    continue
                zf.write(str(blob_path), arcname=rel_path)
    except Exception as e:
        _cleanup()
        raise HTTPException(status_code=500, detail=f"Failed to create zip: {e}")

    if download_name:
        final_name = download_name
    else:
        source_path = manifest.get("source_path", "")
        final_name = Path(source_path).name if source_path else manifest.get("fingerprint", "archive")[:16]

    if not final_name.lower().endswith(".zip"):
        final_name = f"{final_name}.zip"

    return FileResponse(
        path=str(tmp_zip),
        filename=final_name,
        media_type="application/zip",
        background=BackgroundTask(_cleanup),
    )
