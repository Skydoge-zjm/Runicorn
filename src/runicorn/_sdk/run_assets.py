from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..assets.archive import archive_dir, archive_file
from ..assets.fingerprint import dir_stat_fingerprint, stat_fingerprint


def scan_outputs_once_impl(
    run: Any,
    *,
    output_dirs: List[Union[str, Path]],
    patterns: Optional[List[str]],
    stable_required: int,
    min_age_sec: float,
    mode: str,
    log_snapshot_interval_sec: float,
    state_gc_after_sec: float,
    scan_outputs_once_fn,
    logger: logging.Logger,
) -> Dict[str, Any]:
    if run.is_finished:
        logger.warning("scan_outputs_once called after finish(); ignoring")
        return {}

    res = scan_outputs_once_fn(
        run_id=run.id,
        run_dir=run.run_dir,
        storage_root=run.storage_root,
        workspace_root=run.workspace_root,
        output_dirs=output_dirs,
        assets_path=run._assets_path,
        assets_lock=run._assets_lock,
        state_path=run._outputs_state_path,
        state_lock=run._outputs_state_lock,
        patterns=patterns,
        stable_required=stable_required,
        min_age_sec=min_age_sec,
        mode=mode,
        log_snapshot_interval_sec=log_snapshot_interval_sec,
        state_gc_after_sec=state_gc_after_sec,
        should_stop=run.should_stop_output_watch,
    )

    if run.should_stop_output_watch():
        return res

    if run.storage_backend:
        try:
            for e in res.get("archived_entries") or []:
                key = e.get("key")
                if key and hasattr(run.storage_backend, "unlink_run_asset"):
                    assets = run.list_storage_assets()
                    for a in assets:
                        if a.get("role") != "output":
                            continue
                        meta = a.get("metadata_json")
                        if isinstance(meta, str):
                            meta = json.loads(meta) if meta else {}
                        elif meta is None:
                            meta = {}
                        if meta.get("key") == key:
                            run.unlink_storage_asset(a["asset_id"])
                            break
                run.record_storage_asset(
                    role="output",
                    asset_type="output",
                    name=e.get("name"),
                    source_uri=e.get("path"),
                    archive_uri=e.get("archive_path"),
                    is_archived=True,
                    fingerprint_kind=e.get("fingerprint_kind"),
                    fingerprint=e.get("fingerprint"),
                    created_at=float(e.get("archived_at") or 0),
                    metadata={"key": e.get("key"), "kind": e.get("kind"), "mode": e.get("mode")},
                )
        except Exception:
            pass

    return res


def watch_outputs_impl(
    run: Any,
    *,
    output_dirs: List[Union[str, Path]],
    interval_sec: float,
    patterns: Optional[List[str]],
    stable_required: int,
    min_age_sec: float,
    mode: str,
    log_snapshot_interval_sec: float,
    state_gc_after_sec: float,
) -> None:
    existing_thread = run.get_output_watch_thread()
    if existing_thread and existing_thread.is_alive():
        return
    run.clear_output_watch_stop()

    def _loop() -> None:
        while not run.should_stop_output_watch():
            try:
                run.scan_outputs_once(
                    output_dirs=output_dirs,
                    patterns=patterns,
                    stable_required=stable_required,
                    min_age_sec=min_age_sec,
                    mode=mode,
                    log_snapshot_interval_sec=log_snapshot_interval_sec,
                    state_gc_after_sec=state_gc_after_sec,
                )
            except Exception:
                pass
            run._outputs_watch_stop.wait(interval_sec)

    t = threading.Thread(target=_loop, daemon=True)
    run.set_output_watch_thread(t)
    t.start()


def stop_outputs_watch_impl(run: Any) -> None:
    run.request_output_watch_stop()
    t = run.get_output_watch_thread()
    if t and t.is_alive():
        t.join(timeout=2.0)


def log_config_impl(
    run: Any,
    *,
    args: Optional[Any],
    extra: Optional[Dict[str, Any]],
    config_files: Optional[List[Union[str, Path]]],
    make_json_safe,
    now_ts,
    logger: logging.Logger,
) -> None:
    if run.is_finished:
        logger.warning("Run already finished, ignoring %s call", "log_config")
        return
    cfg_holder: Dict[str, Any] = {}

    def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
        cfg: Dict[str, Any] = dict((a.get("config") or {}))
        if args is not None:
            raw_args = args if isinstance(args, dict) else vars(args)
            cfg["args"] = make_json_safe(raw_args)
        if extra is not None:
            cfg["extra"] = make_json_safe(extra)
        if config_files is not None:
            cfg["config_files"] = [str(Path(p)) for p in config_files]
        a["config"] = cfg
        cfg_holder.clear()
        cfg_holder.update(cfg)
        return a

    run.update_assets_manifest(_upd)
    if run.storage_backend:
        try:
            run.record_storage_asset(
                role="config",
                asset_type="config",
                name=None,
                source_uri=None,
                archive_uri=None,
                is_archived=False,
                fingerprint_kind=None,
                fingerprint=None,
                created_at=now_ts(),
                metadata=cfg_holder,
            )
        except Exception:
            pass


def log_dataset_impl(
    run: Any,
    *,
    name: str,
    root_or_uri: Union[str, Path, Dict[str, Any]],
    context: str,
    save: bool,
    description: Optional[str],
    force_save: bool,
    max_archive_bytes: int,
    max_archive_files: int,
    now_ts,
    logger: logging.Logger,
) -> None:
    if run.is_finished:
        logger.warning("log_dataset called after finish(); ignoring")
        return
    uri: Any = root_or_uri
    fp: Optional[Dict[str, Any]] = None
    archived: Optional[Dict[str, Any]] = None

    if isinstance(root_or_uri, (str, Path)):
        p = Path(root_or_uri).expanduser()
        uri = str(p)
        try:
            if p.is_dir():
                fp = dir_stat_fingerprint(p)
                if save:
                    if (fp.get("total_size_bytes") or 0) > max_archive_bytes or (fp.get("file_count") or 0) > max_archive_files:
                        if not force_save:
                            raise ValueError("dataset too large to archive; set force_save=True or use save=False")
                    archived = archive_dir(p, run.storage_root / "archive", category="datasets")
            elif p.is_file():
                fp = stat_fingerprint(p)
                if save:
                    if (fp.get("size_bytes") or 0) > max_archive_bytes and not force_save:
                        raise ValueError("dataset file too large to archive; set force_save=True or use save=False")
                    archived = archive_file(p, run.storage_root / "archive", category="datasets")
        except OSError:
            fp = None

    entry: Dict[str, Any] = {
        "name": name,
        "context": context,
        "uri": uri,
        "description": description,
        "saved": bool(save and archived),
        "fingerprint": fp,
    }
    if archived:
        entry.update(archived)

    def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
        a.setdefault("datasets", [])
        a["datasets"].append(entry)
        return a

    run.update_assets_manifest(_upd)
    if run.storage_backend:
        try:
            fp_kind = entry.get("fingerprint_kind")
            fp_val = entry.get("fingerprint")
            if isinstance(fp_val, dict):
                fp_val = json.dumps(fp_val, ensure_ascii=False, sort_keys=True)
                fp_kind = fp_kind or "stat"
            run.record_storage_asset(
                role="dataset",
                asset_type="dataset",
                name=name,
                source_uri=str(entry.get("uri")) if entry.get("uri") is not None else None,
                archive_uri=entry.get("archive_path"),
                is_archived=bool(entry.get("saved")),
                fingerprint_kind=fp_kind,
                fingerprint=fp_val,
                created_at=now_ts(),
                metadata={"context": context, "description": description},
            )
        except Exception:
            pass


def log_pretrained_impl(
    run: Any,
    *,
    name: str,
    path_or_uri: Optional[Union[str, Path, Dict[str, Any]]],
    save: bool,
    source_type: str,
    description: Optional[str],
    force_save: bool,
    max_archive_bytes: int,
    max_archive_files: int,
    now_ts,
    logger: logging.Logger,
) -> None:
    if run.is_finished:
        logger.warning("log_pretrained called after finish(); ignoring")
        return
    archived: Optional[Dict[str, Any]] = None

    if save and path_or_uri is None:
        raise ValueError("save=True requires path_or_uri")

    if save and isinstance(path_or_uri, (str, Path)):
        p = Path(path_or_uri).expanduser()
        if p.is_dir():
            fp = dir_stat_fingerprint(p)
            if (fp.get("total_size_bytes") or 0) > max_archive_bytes or (fp.get("file_count") or 0) > max_archive_files:
                if not force_save:
                    raise ValueError("pretrained dir too large to archive; set force_save=True or use save=False")
            archived = archive_dir(p, run.storage_root / "archive", category="pretrained")
        elif p.is_file():
            fp2 = stat_fingerprint(p)
            if (fp2.get("size_bytes") or 0) > max_archive_bytes and not force_save:
                raise ValueError("pretrained file too large to archive; set force_save=True or use save=False")
            archived = archive_file(p, run.storage_root / "archive", category="pretrained")

    entry: Dict[str, Any] = {
        "name": name,
        "source_type": source_type,
        "path_or_uri": None
        if path_or_uri is None
        else (str(path_or_uri) if isinstance(path_or_uri, (str, Path)) else path_or_uri),
        "description": description,
        "saved": bool(save and archived),
    }
    if archived:
        entry.update(archived)

    def _upd(a: Dict[str, Any]) -> Dict[str, Any]:
        a.setdefault("pretrained", [])
        a["pretrained"].append(entry)
        return a

    run.update_assets_manifest(_upd)
    if run.storage_backend:
        try:
            run.record_storage_asset(
                role="pretrained",
                asset_type="pretrained",
                name=name,
                source_uri=str(entry.get("path_or_uri")) if entry.get("path_or_uri") is not None else None,
                archive_uri=entry.get("archive_path"),
                is_archived=bool(entry.get("saved")),
                fingerprint_kind=entry.get("fingerprint_kind"),
                fingerprint=entry.get("fingerprint"),
                created_at=now_ts(),
                metadata={"source_type": source_type, "description": description},
            )
        except Exception:
            pass
