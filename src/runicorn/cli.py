from __future__ import annotations

import argparse
import os
import sys
import tarfile
import zipfile
import time
from pathlib import Path
from typing import Optional, Iterable

import uvicorn

from .viewer import create_app
from .config import get_config_file_path, load_user_config, set_user_root_dir
from .sdk import _default_storage_dir


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="runicorn", description="Runicorn CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_viewer = sub.add_parser("viewer", help="Start the local read-only viewer API")
    p_viewer.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or None, help="Storage root directory; if omitted, uses global config or legacy ./.runicorn")
    p_viewer.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    p_viewer.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    p_viewer.add_argument("--reload", action="store_true", help="Enable auto-reload (dev only)")

    p_cfg = sub.add_parser("config", help="Manage Runicorn user configuration")
    p_cfg.add_argument("--show", action="store_true", help="Show current configuration")
    p_cfg.add_argument("--set-user-root", dest="user_root", help="Set the per-user root directory for all projects")

    p_exp = sub.add_parser("export", help="Export runs into a .tar.gz for offline transfer")
    p_exp.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or None, help="Storage root directory; if omitted, uses global config or legacy ./.runicorn")
    p_exp.add_argument("--project", help="Filter by project (new layout)")
    p_exp.add_argument("--name", help="Filter by experiment name (new layout)")
    p_exp.add_argument("--run-id", dest="run_ids", action="append", help="Export only specific run id(s); can be set multiple times")
    p_exp.add_argument("--out", dest="out_path", help="Output archive path (.tar.gz). Default: runicorn_export_<ts>.tar.gz")

    p_imp = sub.add_parser("import", help="Import an archive (.zip/.tar.gz) of runs into storage")
    p_imp.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or None, help="Target storage root; if omitted, uses global config or legacy ./.runicorn")
    p_imp.add_argument("--archive", required=True, help="Path to the .zip or .tar.gz archive to import")

    args = parser.parse_args(argv)

    if args.cmd == "viewer":
        # uvicorn can serve factory via --factory style; do it programmatically here
        app = lambda: create_app(storage=args.storage)  # noqa: E731
        uvicorn.run(app, host=args.host, port=args.port, reload=bool(args.reload), factory=True)
        return 0

    if args.cmd == "config":
        did = False
        if getattr(args, "user_root", None):
            p = set_user_root_dir(args.user_root)
            print(f"Set user_root_dir to: {p}")
            did = True
        if getattr(args, "show", False) or not did:
            cfg_file = get_config_file_path()
            cfg = load_user_config()
            print("Runicorn user config:")
            print(f"  File          : {cfg_file}")
            print(f"  user_root_dir : {cfg.get('user_root_dir') or '(not set)'}")
            if not cfg.get('user_root_dir'):
                print("\nTip: Set it via:\n  runicorn config --set-user-root <ABSOLUTE_PATH>")
        return 0

    if args.cmd == "export":
        root = _default_storage_dir(getattr(args, "storage", None))
        root.mkdir(parents=True, exist_ok=True)

        # Discover candidate run directories (new + legacy)
        candidates: list[Path] = []
        # New layout: root/<project>/<name>/runs/<id>
        try:
            for proj in sorted([p for p in root.iterdir() if p.is_dir()]):
                if proj.name in {"runs", "webui"}:
                    continue
                if args.project and proj.name != args.project:
                    continue
                for name in sorted([n for n in proj.iterdir() if n.is_dir()]):
                    if args.name and name.name != args.name:
                        continue
                    runs_dir = name / "runs"
                    if not runs_dir.exists():
                        continue
                    for rd in runs_dir.iterdir():
                        if not rd.is_dir():
                            continue
                        if args.run_ids and rd.name not in set(args.run_ids):
                            continue
                        candidates.append(rd)
        except Exception:
            pass
        # Legacy: root/runs/<id>
        try:
            legacy_runs = root / "runs"
            if legacy_runs.exists():
                for rd in legacy_runs.iterdir():
                    if not rd.is_dir():
                        continue
                    if args.run_ids and rd.name not in set(args.run_ids):
                        continue
                    # If filters (project/name) are set, legacy runs won't match; include only if no filters
                    if (args.project or args.name):
                        continue
                    candidates.append(rd)
        except Exception:
            pass

        if not candidates:
            print("No runs matched the given filters. Nothing to export.")
            return 0

        out_path = args.out_path or f"runicorn_export_{int(time.time())}.tar.gz"
        out = Path(out_path).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        print(f"Exporting {len(candidates)} run(s) to {out} ...")
        # Create tar.gz with paths relative to storage root, so import can merge directly
        with tarfile.open(out, "w:gz") as tf:
            for rd in candidates:
                try:
                    arcname = rd.relative_to(root)
                except Exception:
                    # If not under root (shouldn't happen), fallback to name
                    arcname = Path(rd.name)
                tf.add(str(rd), arcname=str(arcname))
        print("Done.")
        return 0

    if args.cmd == "import":
        root = _default_storage_dir(getattr(args, "storage", None))
        root.mkdir(parents=True, exist_ok=True)
        archive = Path(getattr(args, "archive")).expanduser().resolve()
        if not archive.exists():
            print(f"Archive not found: {archive}")
            return 1

        def is_within(base: Path, target: Path) -> bool:
            try:
                return str(target.resolve()).startswith(str(base.resolve()))
            except Exception:
                return False

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
                        if not is_within(root, target):
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
                        if not is_within(root, target):
                            continue
                        tf.extract(member, path=str(root))
                        if not member.isdir():
                            imported += 1
            print(f"Imported {imported} files into {root}")
            return 0
        except Exception as e:
            print(f"Import failed: {e}")
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
