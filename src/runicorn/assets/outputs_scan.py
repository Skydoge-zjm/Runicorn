from __future__ import annotations

import fnmatch
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from filelock import FileLock

from .archive import (
    archive_dir,
    archive_dir_overwrite,
    archive_file,
    archive_file_overwrite,
    archive_file_overwrite_stat,
)
from .assets_json import update_assets_atomic


def _now() -> float:
    return time.time()


def _posix(p: Path) -> str:
    return p.as_posix()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def _match_any(rel_posix: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if pat.startswith("**/"):
            if fnmatch.fnmatchcase(rel_posix, pat[3:]):
                return True
        if fnmatch.fnmatchcase(rel_posix, pat):
            return True
    return False


def _default_patterns() -> List[str]:
    return [
        "*.pth",
        "**/*.pth",
        "*.pt",
        "**/*.pt",
        "*.ckpt",
        "**/*.ckpt",
        "*.onnx",
        "**/*.onnx",
        "*.log",
        "**/*.log",
        "*.json",
        "**/*.json",
        "*.txt",
        "**/*.txt",
        "*.csv",
        "**/*.csv",
        "*.png",
        "**/*.png",
    ]


def _split_patterns(patterns: List[str]) -> Tuple[List[str], List[str]]:
    file_pats: List[str] = []
    dir_pats: List[str] = []
    for p in patterns:
        if p.endswith("/"):
            dir_pats.append(p)
        else:
            file_pats.append(p)
    return file_pats, dir_pats


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"items": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"items": {}}


def _save_state(path: Path, lock: FileLock, state: Dict[str, Any]) -> None:
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.stem}_",
        suffix=".json.tmp",
        text=False,
    )
    try:
        os.close(tmp_fd)
        Path(tmp_path).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        Path(tmp_path).replace(path)
    finally:
        try:
            p = Path(tmp_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass


def _is_log_like(path: Path) -> bool:
    name = path.name
    if "tfevents" in name:
        return True
    suf = path.suffix.lower()
    if suf in {".log", ".txt", ".jsonl", ".csv"}:
        return True
    return False


def _upsert_output_entry(outputs: List[Dict[str, Any]], key: str, new_entry: Dict[str, Any], mode: str) -> None:
    idx = None
    for i, it in enumerate(outputs):
        if it.get("key") == key:
            idx = i
            break

    if idx is None:
        outputs.append(new_entry)
        return

    if mode == "overwrite_versions":
        outputs.append(new_entry)
        return

    outputs[idx] = new_entry


def scan_outputs_once(
    *,
    run_id: str,
    run_dir: Path,
    storage_root: Path,
    workspace_root: Path,
    output_dirs: List[Union[str, Path]],
    assets_path: Path,
    assets_lock: FileLock,
    state_path: Path,
    state_lock: FileLock,
    patterns: Optional[List[str]] = None,
    stable_required: int = 2,
    min_age_sec: float = 1.0,
    mode: str = "rolling",
    log_snapshot_interval_sec: float = 60.0,
    state_gc_after_sec: float = 7 * 24 * 3600,
) -> Dict[str, Any]:
    all_pats = patterns or _default_patterns()
    file_pats, dir_pats = _split_patterns(all_pats)

    with state_lock:
        state = _load_state(state_path)
        items: Dict[str, Any] = state.setdefault("items", {})

        now = _now()
        changed = 0
        scanned = 0
        archived_n = 0
        archived_entries: List[Dict[str, Any]] = []

        for od in output_dirs:
            odir = Path(od).expanduser().resolve()
            if not odir.exists():
                continue

            for dirpath, dirnames, filenames in os.walk(odir):
                dp = Path(dirpath)

                rel_dir = dp.relative_to(odir).as_posix() if dp != odir else ""
                for d in list(dirnames):
                    rel = f"{rel_dir}/{d}" if rel_dir else d
                    if dir_pats and _match_any(rel + "/", dir_pats):
                        scanned += 1
                        dir_path = dp / d
                        try:
                            st = dir_path.stat()
                        except OSError:
                            continue

                        key_path: Path = dir_path
                        if _is_within(dir_path, workspace_root):
                            key_path = dir_path.resolve().relative_to(workspace_root.resolve())
                        key = _posix(key_path)

                        it = items.get(key) or {}
                        last_mtime_ns = it.get("last_mtime_ns")
                        stable_count = int(it.get("stable_count") or 0)
                        cur_mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
                        age = now - float(st.st_mtime)
                        if age < 0:
                            age = 0.0

                        if last_mtime_ns == cur_mtime_ns:
                            stable_count += 1
                        else:
                            stable_count = 1

                        it["last_mtime_ns"] = cur_mtime_ns
                        it["stable_count"] = stable_count
                        it["last_seen_at"] = now

                        if age < min_age_sec or stable_count < stable_required:
                            items[key] = it
                            continue

                        try:
                            if mode == "rolling":
                                archived = archive_dir_overwrite(
                                    dir_path,
                                    storage_root / "archive",
                                    category="outputs",
                                    run_id=run_id,
                                    key=key,
                                )
                            else:
                                archived = archive_dir(dir_path, storage_root / "archive", category="outputs")
                        except Exception as e:
                            it["last_error"] = str(e)
                            items[key] = it
                            continue

                        fp = archived.get("fingerprint")
                        if fp and it.get("last_archived_fingerprint") == fp:
                            items[key] = it
                            continue

                        it["last_archived_fingerprint"] = fp
                        it["last_archived_at"] = now
                        it.pop("last_error", None)
                        items[key] = it

                        if _is_within(dir_path, workspace_root):
                            display_path = "./" + dir_path.resolve().relative_to(workspace_root.resolve()).as_posix()
                        else:
                            display_path = dir_path.as_posix()

                        entry = {
                            "key": key,
                            "name": Path(display_path).name,
                            "kind": "dir",
                            "path": display_path,
                            "saved": True,
                            "archive_path": archived.get("archive_path"),
                            "fingerprint_kind": archived.get("fingerprint_kind"),
                            "fingerprint": archived.get("fingerprint"),
                            "mode": mode,
                            "archived_at": int(now),
                        }

                        def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
                            outputs = a.setdefault("outputs", [])
                            _upsert_output_entry(outputs, key, entry, mode)
                            return a

                        update_assets_atomic(assets_path, assets_lock, _upd)

                        archived_entries.append(entry)
                        archived_n += 1
                        changed += 1

                for fn in filenames:
                    src = dp / fn
                    try:
                        st = src.stat()
                    except OSError:
                        continue

                    rel = src.relative_to(odir).as_posix()
                    if not _match_any(rel, file_pats):
                        continue

                    scanned += 1
                    key_path = src
                    if _is_within(src, workspace_root):
                        key_path = src.resolve().relative_to(workspace_root.resolve())
                    key = _posix(key_path)

                    it = items.get(key) or {}
                    it["last_seen_at"] = now

                    is_log = _is_log_like(src)
                    if is_log:
                        last_snap = float(it.get("last_log_snapshot_at") or 0.0)
                        if log_snapshot_interval_sec > 0 and (now - last_snap) < float(log_snapshot_interval_sec):
                            items[key] = it
                            continue
                        try:
                            archived = archive_file_overwrite_stat(
                                src,
                                storage_root / "archive",
                                category="outputs",
                                run_id=run_id,
                                key=key,
                            )
                        except Exception as e:
                            it["last_error"] = str(e)
                            items[key] = it
                            continue

                        fp = archived.get("fingerprint")
                        if fp and it.get("last_archived_fingerprint") == fp:
                            it["last_log_snapshot_at"] = now
                            it.pop("last_error", None)
                            items[key] = it
                            continue

                        it["last_archived_fingerprint"] = fp
                        it["last_archived_at"] = now
                        it["last_log_snapshot_at"] = now
                        it.pop("last_error", None)
                        items[key] = it

                        if _is_within(src, workspace_root):
                            display_path = "./" + src.resolve().relative_to(workspace_root.resolve()).as_posix()
                        else:
                            display_path = src.as_posix()

                        entry = {
                            "key": key,
                            "name": Path(display_path).name,
                            "kind": "file",
                            "path": display_path,
                            "saved": True,
                            "archive_path": archived.get("archive_path"),
                            "fingerprint_kind": archived.get("fingerprint_kind"),
                            "fingerprint": archived.get("fingerprint"),
                            "mode": "rolling",
                            "archived_at": int(now),
                        }

                        def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
                            outputs = a.setdefault("outputs", [])
                            _upsert_output_entry(outputs, key, entry, "rolling")
                            return a

                        update_assets_atomic(assets_path, assets_lock, _upd)

                        archived_entries.append(entry)
                        archived_n += 1
                        changed += 1
                        continue

                    last_size = it.get("last_size")
                    last_mtime_ns = it.get("last_mtime_ns")
                    stable_count = int(it.get("stable_count") or 0)

                    cur_size = int(st.st_size)
                    cur_mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
                    age = now - float(st.st_mtime)
                    if age < 0:
                        age = 0.0

                    if last_size == cur_size and last_mtime_ns == cur_mtime_ns:
                        stable_count += 1
                    else:
                        stable_count = 1

                    it["last_size"] = cur_size
                    it["last_mtime_ns"] = cur_mtime_ns
                    it["stable_count"] = stable_count

                    if age < min_age_sec or stable_count < stable_required:
                        items[key] = it
                        continue

                    try:
                        if mode == "rolling":
                            archived = archive_file_overwrite(
                                src,
                                storage_root / "archive",
                                category="outputs",
                                run_id=run_id,
                                key=key,
                            )
                        else:
                            archived = archive_file(src, storage_root / "archive", category="outputs")
                    except Exception as e:
                        it["last_error"] = str(e)
                        items[key] = it
                        continue

                    fp = archived.get("fingerprint")
                    if fp and it.get("last_archived_fingerprint") == fp:
                        it.pop("last_error", None)
                        items[key] = it
                        continue

                    it["last_archived_fingerprint"] = fp
                    it["last_archived_at"] = now
                    it.pop("last_error", None)
                    items[key] = it

                    if _is_within(src, workspace_root):
                        display_path = "./" + src.resolve().relative_to(workspace_root.resolve()).as_posix()
                    else:
                        display_path = src.as_posix()

                    entry = {
                        "key": key,
                        "name": Path(display_path).name,
                        "kind": "file",
                        "path": display_path,
                        "saved": True,
                        "archive_path": archived.get("archive_path"),
                        "fingerprint_kind": archived.get("fingerprint_kind"),
                        "fingerprint": archived.get("fingerprint"),
                        "mode": mode,
                        "archived_at": int(now),
                    }

                    def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
                        outputs = a.setdefault("outputs", [])
                        _upsert_output_entry(outputs, key, entry, mode)
                        return a

                    update_assets_atomic(assets_path, assets_lock, _upd)

                    archived_entries.append(entry)
                    archived_n += 1
                    changed += 1

        if state_gc_after_sec and state_gc_after_sec > 0:
            cutoff = now - float(state_gc_after_sec)
            for k in list(items.keys()):
                try:
                    if float(items.get(k, {}).get("last_seen_at") or 0) < cutoff:
                        items.pop(k, None)
                except Exception:
                    pass

        _save_state(state_path, state_lock, state)

        return {
            "run_id": run_id,
            "scanned": scanned,
            "archived": archived_n,
            "changed": changed,
            "archived_entries": archived_entries,
        }
