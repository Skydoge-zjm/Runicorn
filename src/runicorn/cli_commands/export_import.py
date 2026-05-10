from __future__ import annotations

import tarfile
import time
import zipfile
from inspect import signature
from pathlib import Path
from typing import Any, Callable, Iterable


def handle_export(
    args: Any,
    *,
    default_storage_dir: Callable[[str | None], Path],
    iter_all_runs_fn: Callable[[Path], Iterable[Any]],
) -> int:
    root = default_storage_dir(getattr(args, "storage", None))
    root.mkdir(parents=True, exist_ok=True)

    candidates: list[Path] = []
    run_id_filter = set(args.run_ids) if args.run_ids else None

    for entry in iter_all_runs_fn(root):
        if run_id_filter and entry.dir.name not in run_id_filter:
            continue
        if args.project and entry.project != args.project:
            continue
        if args.name and entry.name != args.name:
            continue
        candidates.append(entry.dir)

    if not candidates:
        print("No runs matched the given filters. Nothing to export.")
        return 0

    out_path = args.out_path or f"runicorn_export_{int(time.time())}.tar.gz"
    out = Path(out_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"Exporting {len(candidates)} run(s) to {out} ...")
    with tarfile.open(out, "w:gz") as tf:
        for rd in candidates:
            try:
                arcname = rd.relative_to(root)
            except Exception:
                arcname = Path(rd.name)
            tf.add(str(rd), arcname=str(arcname))
    print("Done.")
    return 0


def handle_import(
    args: Any,
    *,
    default_storage_dir: Callable[[str | None], Path],
) -> int:
    root = default_storage_dir(getattr(args, "storage", None))
    root.mkdir(parents=True, exist_ok=True)
    archive = Path(getattr(args, "archive")).expanduser().resolve()
    if not archive.exists():
        print(f"Archive not found: {archive}")
        return 1

    imported = 0
    try:
        fn = archive.name.lower()
        if fn.endswith(".zip"):
            with zipfile.ZipFile(str(archive), "r") as zf:
                for name in zf.namelist():
                    if not name or name.endswith("/"):
                        try:
                            (root / name).mkdir(parents=True, exist_ok=True)
                        except Exception:
                            pass
                        continue
                    target = root / name
                    if not _is_within(root, target):
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, open(target, "wb") as out:
                        out.write(src.read())
                    imported += 1
        else:
            mode = "r:gz" if (fn.endswith(".tar.gz") or fn.endswith(".tgz")) else "r"
            with tarfile.open(str(archive), mode) as tf:
                for member in tf.getmembers():
                    if not member.name:
                        continue
                    try:
                        if member.issym() or member.islnk():
                            continue
                    except Exception:
                        pass
                    target = root / member.name
                    if not _is_within(root, target):
                        continue
                    _extract_tar_member(tf, member, root)
                    if not member.isdir():
                        imported += 1
        print(f"Imported {imported} files into {root}")
        return 0
    except Exception as e:
        print(f"Import failed: {e}")
        return 1


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


_TAR_EXTRACT_SUPPORTS_FILTER = "filter" in signature(tarfile.TarFile.extract).parameters


def _extract_tar_member(tf: tarfile.TarFile, member: tarfile.TarInfo, root: Path) -> None:
    if _TAR_EXTRACT_SUPPORTS_FILTER:
        tf.extract(member, path=str(root), filter="data")
        return
    tf.extract(member, path=str(root))
