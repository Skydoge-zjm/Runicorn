from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .ignore import ensure_rnignore, load_ignore_matcher


def snapshot_workspace(
    root: Path,
    out_zip: Path,
    *,
    ignore_file: str = ".rnignore",
    extra_excludes: Optional[List[str]] = None,
    max_total_bytes: int = 500 * 1024 * 1024,
    max_files: int = 200_000,
    force_snapshot: bool = False,
) -> Dict[str, Any]:
    root = Path(root).resolve()
    out_zip = Path(out_zip).resolve()

    ensure_rnignore(root, rnignore_name=ignore_file)

    matcher = load_ignore_matcher(root, rnignore_name=ignore_file, extra_excludes=extra_excludes)

    files: List[Tuple[Path, str]] = []
    total_bytes = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirpath_p = Path(dirpath)
        rel_dir = dirpath_p.relative_to(root).as_posix()

        kept_dirnames: List[str] = []
        for d in dirnames:
            rel = f"{rel_dir}/{d}" if rel_dir else d
            if matcher.is_ignored(rel, is_dir=True):
                continue
            kept_dirnames.append(d)
        dirnames[:] = kept_dirnames

        for fn in filenames:
            src = dirpath_p / fn
            rel = f"{rel_dir}/{fn}" if rel_dir else fn
            if matcher.is_ignored(rel, is_dir=False):
                continue

            try:
                st = src.stat()
            except OSError:
                continue

            files.append((src, rel))
            total_bytes += int(st.st_size)

            if not force_snapshot:
                if len(files) > max_files:
                    raise ValueError("code snapshot too large: too many files")
                if total_bytes > max_total_bytes:
                    raise ValueError("code snapshot too large: total bytes exceeded")

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src, rel in files:
            zf.write(src, rel)

    return {
        "workspace_root": str(root),
        "archive_path": str(out_zip),
        "format": "zip",
        "file_count": len(files),
        "total_bytes": int(total_bytes),
    }
