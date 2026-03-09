"""
Import/Export Archive API Routes

Handles import of experiment archives (zip/tar.gz) into the storage system.
"""
from __future__ import annotations

import logging
import re
import secrets
import tarfile
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form

from ...storage.file_utils import iter_all_runs, read_json, write_json, is_run_deleted
from ..utils.helpers import is_within_directory
from ..services.db_reader import get_backend, sync_filesystem_to_db

logger = logging.getLogger(__name__)
router = APIRouter()

PREVIEW_TOKEN_TTL_SECONDS = 30 * 60

# Check if multipart support is available
try:
    import multipart  # type: ignore
    HAS_MULTIPART = True
except ImportError:
    HAS_MULTIPART = False
    logger.debug("python-multipart not available, file upload disabled")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_archive_name(name: str) -> str:
    norm = (name or "").replace("\\", "/").strip()
    while norm.startswith("./"):
        norm = norm[2:]
    return norm.lstrip("/")


_UUID_LIKE_RE = re.compile(
    r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$"
)


def _looks_like_run_id(segment: str) -> bool:
    """Check if a path segment looks like a run ID (UUID or similar)."""
    if not segment or len(segment) < 8:
        return False
    if _UUID_LIKE_RE.match(segment):
        return True
    return bool(re.match(r"^[a-fA-F0-9\-]{20,}$", segment))


def _default_path_mapper(name: str) -> Optional[str]:
    """
    Map archive entry paths to storage layout.

    Export ZIP writes runs as <run_id>/... (no runs/ prefix).
    Standard layout expects runs/<path>/<run_id>/ or runs/<run_id>/.
    This mapper detects export format and prepends runs/ when missing.
    """
    norm = _normalize_archive_name(name)
    if not norm:
        return None
    if norm.startswith("runs/"):
        return norm
    if "/runs/" in norm:
        rel = norm.split("/runs/", 1)[1]
        return f"runs/{rel}"
    parts = norm.split("/", 1)
    if len(parts) == 2:
        first, rest = parts
        if first.lower() in ("index.json",):
            return norm
        if _looks_like_run_id(first):
            return f"runs/{norm}"
    elif len(parts) == 1 and parts[0].lower() != "index.json":
        if _looks_like_run_id(parts[0]):
            return f"runs/{norm}"
    return norm


def _build_isolate_mapper(import_ts: str) -> Callable[[str], Optional[str]]:
    """Build a path mapper that rewrites archive entries under runs/imports/<ts>/."""
    isolate_prefix = f"runs/imports/{import_ts}"

    def _mapper(name: str) -> Optional[str]:
        norm = _normalize_archive_name(name)
        if not norm:
            return None
        # Preferred: runs/<path>/<run_id>/...
        if norm.startswith("runs/"):
            rel = norm[len("runs/"):]
        # Legacy: <project>/<name>/runs/<run_id>/...
        elif "/runs/" in norm:
            rel = norm.split("/runs/", 1)[1]
        else:
            rel = norm
        rel = rel.strip("/")
        if not rel:
            return None
        return f"{isolate_prefix}/{rel}"

    return _mapper


# --- Preview token store (in-memory, per-process) ---

def _get_preview_store(app_state: Any) -> Dict[str, Dict[str, Any]]:
    store = getattr(app_state, "import_preview_store", None)
    if store is None or not isinstance(store, dict):
        store = {}
        setattr(app_state, "import_preview_store", store)
    return store


def _cleanup_preview_store(app_state: Any) -> None:
    store = _get_preview_store(app_state)
    now = time.time()
    expired = [
        tok for tok, meta in store.items()
        if (now - float(meta.get("created_at", 0))) > PREVIEW_TOKEN_TTL_SECONDS
        or not Path(str(meta.get("path", ""))).exists()
    ]
    for tok in expired:
        meta = store.pop(tok, None)
        if meta:
            try:
                Path(str(meta.get("path", ""))).unlink(missing_ok=True)
            except Exception:
                pass


# --- File I/O helpers ---

async def _save_upload_to_temp(file: UploadFile, suffix: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(prefix="runicorn_import_", suffix=suffix, delete=False)
    tmp_path = Path(tmp.name)
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
    finally:
        tmp.close()
    return tmp_path


def _iter_archive_file_names(tmp_path: Path, filename: str) -> List[str]:
    """List all file entries inside the archive (normalised paths)."""
    names: List[str] = []
    lname = (filename or "").lower()

    def _collect_zip(zf: zipfile.ZipFile) -> None:
        for info in zf.infolist():
            if info.is_dir():
                continue
            n = _normalize_archive_name(info.filename)
            if n:
                names.append(n)

    def _collect_tar(tf: tarfile.TarFile) -> None:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            n = _normalize_archive_name(m.name)
            if n:
                names.append(n)

    if lname.endswith(".zip"):
        with zipfile.ZipFile(tmp_path, "r") as zf:
            _collect_zip(zf)
        return names

    if lname.endswith(".tar.gz") or lname.endswith(".tgz"):
        with tarfile.open(tmp_path, "r:gz") as tf:
            _collect_tar(tf)
        return names

    # Unknown extension – try zip then tar.gz
    try:
        with zipfile.ZipFile(tmp_path, "r") as zf:
            _collect_zip(zf)
        return names
    except Exception:
        pass
    with tarfile.open(tmp_path, "r:gz") as tf:
        _collect_tar(tf)
    return names


# --- Preview analysis ---

def _extract_run_identity(run_dir: str) -> Tuple[str, str]:
    """Return (run_id, path) from an archive run-directory path."""
    parts = [p for p in _normalize_archive_name(run_dir).split("/") if p]
    if not parts:
        return "", ""
    if "runs" in parts:
        idx = parts.index("runs")
        tail = parts[idx + 1:]
        if not tail:
            return "", ""
        return tail[-1], "/".join(tail[:-1])
    return parts[-1], "/".join(parts[:-1])


def _build_import_preview(file_names: List[str], existing_run_ids: set) -> Dict[str, Any]:
    marker_files = ("meta.json", "status.json")
    run_dirs: Dict[str, int] = {}

    for name in file_names:
        lower = name.lower()
        if any(lower.endswith(f"/{m}") for m in marker_files):
            rd = name.rsplit("/", 1)[0] if "/" in name else ""
            if rd:
                run_dirs[rd] = 0

    sorted_keys = sorted(run_dirs.keys(), key=len, reverse=True)
    for name in file_names:
        for rd in sorted_keys:
            if name.startswith(f"{rd}/"):
                run_dirs[rd] += 1
                break

    runs: List[Dict[str, Any]] = []
    conflicts: List[str] = []
    for rd in sorted(run_dirs.keys()):
        run_id, path = _extract_run_identity(rd)
        if not run_id:
            continue
        conflict = run_id in existing_run_ids
        runs.append({"run_id": run_id, "path": path, "files_count": run_dirs[rd], "conflict": conflict})
        if conflict:
            conflicts.append(run_id)

    return {
        "runs": runs,
        "total_runs": len(runs),
        "total_files": len(file_names),
        "conflict_count": len(conflicts),
        "conflict_run_ids": sorted(conflicts),
    }


def _extract_archive_run_ids(file_names: List[str]) -> set:
    """Extract the set of run_ids present in the archive."""
    marker_files = ("meta.json", "status.json")
    run_ids: set = set()
    for name in file_names:
        lower = name.lower()
        if any(lower.endswith(f"/{m}") for m in marker_files):
            rd = name.rsplit("/", 1)[0] if "/" in name else ""
            if rd:
                run_id, _ = _extract_run_identity(rd)
                if run_id:
                    run_ids.add(run_id)
    return run_ids


def _wrap_mapper_skip_ids(
    inner: Callable[[str], Optional[str]],
    skip_ids: set,
) -> Callable[[str], Optional[str]]:
    """Wrap a path mapper to skip archive entries belonging to conflicting run IDs."""
    def _mapper(name: str) -> Optional[str]:
        norm = _normalize_archive_name(name)
        segments = set(norm.split("/"))
        if segments & skip_ids:
            return None
        return inner(name)
    return _mapper


# ---------------------------------------------------------------------------
# Extraction with optional path rewrite
# ---------------------------------------------------------------------------

def safe_extract_tar(
    tar: tarfile.TarFile, dest: Path,
    path_mapper: Optional[Callable[[str], Optional[str]]] = None,
) -> List[Path]:
    extracted: List[Path] = []
    mapper = path_mapper or _default_path_mapper
    for member in tar.getmembers():
        try:
            if member.issym() or member.islnk():
                continue
        except Exception:
            pass
        mapped = mapper(member.name)
        if not mapped:
            continue
        target = dest / mapped
        if not is_within_directory(dest, target):
            continue
        try:
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            src = tar.extractfile(member)
            if src is None:
                continue
            with src, open(target, "wb") as out:
                out.write(src.read())
            extracted.append(target)
        except Exception as e:
            logger.warning(f"Failed to extract {member.name}: {e}")
    return extracted


def safe_extract_zip(
    zf: zipfile.ZipFile, dest: Path,
    path_mapper: Optional[Callable[[str], Optional[str]]] = None,
) -> List[Path]:
    extracted: List[Path] = []
    mapper = path_mapper or _default_path_mapper
    for info in zf.infolist():
        mapped = mapper(info.filename)
        if not mapped:
            continue
        target = dest / mapped
        if not is_within_directory(dest, target):
            continue
        try:
            if info.is_dir() or info.filename.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                out.write(src.read())
            extracted.append(target)
        except Exception as e:
            logger.warning(f"Failed to extract {info.filename}: {e}")
    return extracted


def _extract_archive(
    tmp_path: Path, filename: str, storage_root: Path,
    path_mapper: Callable[[str], Optional[str]],
) -> List[Path]:
    lname = (filename or "").lower()
    if lname.endswith(".zip"):
        with zipfile.ZipFile(tmp_path, "r") as zf:
            return safe_extract_zip(zf, storage_root, path_mapper=path_mapper)
    if lname.endswith(".tar.gz") or lname.endswith(".tgz"):
        with tarfile.open(tmp_path, "r:gz") as tf:
            return safe_extract_tar(tf, storage_root, path_mapper=path_mapper)
    # Unknown – try zip then tar
    try:
        with zipfile.ZipFile(tmp_path, "r") as zf:
            return safe_extract_zip(zf, storage_root, path_mapper=path_mapper)
    except Exception:
        pass
    with tarfile.open(tmp_path, "r:gz") as tf:
        return safe_extract_tar(tf, storage_root, path_mapper=path_mapper)


# ---------------------------------------------------------------------------
# Route definitions
# ---------------------------------------------------------------------------

if HAS_MULTIPART:
    @router.post("/import/preview")
    async def preview_import_archive(request: Request, file: UploadFile = File(...)) -> Dict[str, Any]:
        """Preview archive contents without importing. Returns a one-time token."""
        storage_root = request.app.state.storage_root
        try:
            suffix = ".zip" if file.filename and file.filename.lower().endswith(".zip") else ".tar.gz"
        except Exception:
            suffix = ".zip"

        tmp_path = await _save_upload_to_temp(file, suffix)

        try:
            file_names = _iter_archive_file_names(tmp_path, file.filename or "")
        except Exception as e:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=f"Unsupported or corrupted archive: {e}")

        existing_ids = {e.dir.name for e in iter_all_runs(storage_root, include_deleted=True)}
        preview = _build_import_preview(file_names, existing_ids)

        _cleanup_preview_store(request.app.state)
        store = _get_preview_store(request.app.state)
        token = secrets.token_urlsafe(24)
        store[token] = {"path": str(tmp_path), "filename": file.filename or "", "created_at": time.time()}

        return {"ok": True, "token": token, "filename": file.filename or "", **preview}

    @router.post("/import/archive")
    async def import_archive(
        request: Request,
        file: Optional[UploadFile] = File(default=None),
        mode: str = Form(default="merge"),
        preview_token: Optional[str] = Form(default=None),
    ) -> Dict[str, Any]:
        """
        Import archive into storage.

        Modes:
          merge   – extract into storage root directly (original paths)
          isolate – extract under runs/imports/<timestamp>/...
        """
        storage_root = request.app.state.storage_root
        mode = (mode or "merge").strip().lower()
        if mode not in {"merge", "isolate"}:
            raise HTTPException(status_code=400, detail="mode must be merge or isolate")

        before_entries = iter_all_runs(storage_root)
        before = {e.dir for e in before_entries}
        before_ids = {e.dir.name for e in before_entries}

        # Resolve source file
        tmp_path: Optional[Path] = None
        archive_filename = ""
        if preview_token:
            _cleanup_preview_store(request.app.state)
            store = _get_preview_store(request.app.state)
            meta = store.pop(preview_token, None)
            if not meta:
                raise HTTPException(status_code=400, detail="Invalid or expired preview token")
            tmp_path = Path(str(meta.get("path", "")))
            archive_filename = str(meta.get("filename", ""))
            if not tmp_path.exists():
                raise HTTPException(status_code=400, detail="Preview archive no longer exists")
        else:
            if file is None:
                raise HTTPException(status_code=422, detail="file is required when preview_token is not provided")
            try:
                suffix = ".zip" if file.filename and file.filename.lower().endswith(".zip") else ".tar.gz"
            except Exception:
                suffix = ".zip"
            tmp_path = await _save_upload_to_temp(file, suffix)
            archive_filename = file.filename or ""

        # Build mapper
        import_ts: Optional[str] = None
        if mode == "isolate":
            import_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            mapper = _build_isolate_mapper(import_ts)
        else:
            mapper = _default_path_mapper

        # Compute conflicting run IDs and skip them during extraction
        file_names = _iter_archive_file_names(tmp_path, archive_filename)
        archive_run_ids = _extract_archive_run_ids(file_names)
        skip_ids = archive_run_ids & before_ids
        if skip_ids:
            mapper = _wrap_mapper_skip_ids(mapper, skip_ids)
            logger.info(f"Skipping {len(skip_ids)} duplicate run(s): {sorted(skip_ids)}")

        # Extract
        try:
            imported_files = _extract_archive(tmp_path, archive_filename, storage_root, mapper)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Unsupported or corrupted archive: {e}")
        finally:
            try:
                if tmp_path:
                    tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

        # Remove stale deleted copies for re-imported runs.
        # Unified flow: deleted runs live under .recycle, so stale copies are
        # deleted from there. Keep a legacy fallback for old in-place markers.
        revived_ids: List[str] = []
        for entry in iter_all_runs(storage_root, include_deleted=True):
            if entry.dir.name in archive_run_ids and is_run_deleted(entry.dir):
                try:
                    if ".recycle" in entry.dir.parts:
                        import shutil as _shutil
                        _shutil.rmtree(entry.dir)
                        logger.info(f"Removed stale .recycle copy for re-imported run: {entry.dir.name}")
                    else:
                        # Legacy compatibility: old soft-deletes were in-place.
                        (entry.dir / ".deleted").unlink()
                        logger.info(f"Removed legacy in-place .deleted marker for re-imported run: {entry.dir.name}")
                    revived_ids.append(entry.dir.name)
                except Exception:
                    pass

        # Restore re-imported runs in DB
        if revived_ids:
            backend = get_backend(request)
            if backend is not None:
                for rid in revived_ids:
                    try:
                        backend.restore_experiments([rid])
                    except Exception:
                        pass

        # Delta
        after_entries = iter_all_runs(storage_root)
        after = {e.dir for e in after_entries}
        new_set = after - before
        new_dirs = sorted(str(p) for p in new_set)
        new_ids = sorted(e.dir.name for e in after_entries if e.dir in new_set)

        # Patch meta.json path so DB sync picks up the correct filesystem path
        for entry in after_entries:
            if entry.dir not in new_set:
                continue
            meta_path = entry.dir / "meta.json"
            meta = read_json(meta_path)
            if isinstance(meta, dict) and meta.get("path") != entry.path:
                meta["path"] = entry.path
                write_json(meta_path, meta)

        logger.info(f"Import completed: {len(imported_files)} files, {len(new_ids)} new runs, mode={mode}")

        # Ensure imported runs are in DB with correct path
        backend = get_backend(request)
        if backend is not None:
            # First, sync new runs into DB (synchronous — fast for a handful of runs)
            try:
                sync_filesystem_to_db(storage_root, backend)
            except Exception as e:
                logger.debug(f"Post-import sync failed: {e}")
            # Force-update path + run_dir ONLY for truly new run_ids
            # (skip duplicates to avoid overwriting original records)
            for entry in after_entries:
                if entry.dir not in new_set:
                    continue
                run_id = entry.dir.name
                if run_id in before_ids:
                    continue  # duplicate — don't touch the original DB record
                try:
                    backend.update_experiment(run_id, {
                        "path": entry.path or "default",
                        "run_dir": str(entry.dir),
                    })
                except Exception:
                    pass

        return {
            "ok": True,
            "imported_files": len(imported_files),
            "new_run_dirs": new_dirs,
            "new_run_ids": new_ids,
            "skipped_run_ids": sorted(skip_ids),
            "skipped_count": len(skip_ids),
            "storage": str(storage_root),
            "mode": mode,
            "isolate_base": f"imports/{import_ts}" if import_ts else None,
        }

else:
    @router.post("/import/preview")
    async def import_preview_unavailable() -> Dict[str, Any]:
        raise HTTPException(status_code=503, detail="File upload not available: python-multipart not bundled")

    @router.post("/import/archive")
    async def import_archive_unavailable() -> Dict[str, Any]:
        raise HTTPException(status_code=503, detail="File upload not available: python-multipart not bundled")
