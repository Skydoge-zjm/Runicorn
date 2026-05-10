from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import uvicorn

from ._version import __version__
from .cli_commands.export_import import handle_export, handle_import
from .cli_commands.manage_delete import handle_delete, handle_manage
from .cli_commands.rate_limit import handle_rate_limit
from .viewer import create_app
from .config import get_config_file_path, load_user_config, set_user_root_dir
from .sdk import _default_storage_dir
from .storage.file_utils import iter_all_runs, find_run_dir_by_id

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runicorn", description="Runicorn CLI")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_viewer = sub.add_parser("viewer", help="Start the local read-only viewer API")
    p_viewer.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or None, help="Storage root directory; if omitted, uses global config or legacy ./.runicorn")
    p_viewer.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    p_viewer.add_argument("--port", type=int, default=23300, help="Port to bind (default: 23300)")
    p_viewer.add_argument("--reload", action="store_true", help="Enable auto-reload (dev only)")
    p_viewer.add_argument("--remote-mode", action="store_true", help="Remote mode: bind only to 127.0.0.1 and enable auto-shutdown")
    p_viewer.add_argument("--idle-timeout", type=int, default=1800, help="Idle timeout in seconds for remote-mode auto-shutdown (default: 1800)")
    p_viewer.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level (default: INFO)")

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
    
    # Export data subcommand
    p_data = sub.add_parser("export-data", help="Export run metrics to CSV or Excel")
    p_data.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or None, help="Storage root directory")
    p_data.add_argument("--run-id", required=True, help="Run ID to export")
    p_data.add_argument("--format", choices=["csv", "excel", "markdown", "html"], default="csv", help="Export format")
    p_data.add_argument("--output", help="Output file path (default: auto-generated)")
    
    # Manage experiments subcommand
    p_manage = sub.add_parser("manage", help="Manage experiments (tag, search, delete)")
    p_manage.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or None, help="Storage root directory")
    p_manage.add_argument("--action", choices=["tag", "search", "delete", "cleanup"], required=True, help="Management action")
    p_manage.add_argument("--run-id", help="Run ID for tagging")
    p_manage.add_argument("--tags", help="Comma-separated tags")
    p_manage.add_argument("--project", help="Filter by project")
    p_manage.add_argument("--text", help="Search text")
    p_manage.add_argument("--days", type=int, default=30, help="Days for cleanup (default: 30)")
    p_manage.add_argument("--dry-run", action="store_true", help="Preview cleanup without deleting")
    
    # Rate limit management subcommand
    p_rate = sub.add_parser("rate-limit", help="Manage API rate limits")
    p_rate.add_argument("--action", choices=["show", "list", "get", "set", "remove", "settings", "reset", "validate"], 
                       default="show", help="Rate limit action (default: show)")
    p_rate.add_argument("--endpoint", help="API endpoint path (e.g., /api/remote/connect)")
    p_rate.add_argument("--max-requests", type=int, help="Maximum requests allowed")
    p_rate.add_argument("--window", type=int, default=60, help="Time window in seconds (default: 60)")
    p_rate.add_argument("--burst", type=int, help="Burst size limit")
    p_rate.add_argument("--description", help="Description of the limit")
    p_rate.add_argument("--enable", action="store_true", help="Enable rate limiting")
    p_rate.add_argument("--disable", action="store_true", help="Disable rate limiting")
    p_rate.add_argument("--log-violations", action="store_true", help="Log rate limit violations")
    p_rate.add_argument("--no-log-violations", action="store_true", help="Don't log rate limit violations")
    p_rate.add_argument("--whitelist-localhost", action="store_true", help="Whitelist localhost")
    p_rate.add_argument("--no-whitelist-localhost", action="store_true", help="Don't whitelist localhost")

    # Delete run with assets subcommand
    p_delete = sub.add_parser("delete", help="Permanently delete runs and their orphaned assets")
    p_delete.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or None, help="Storage root directory")
    p_delete.add_argument("--run-id", dest="run_ids", action="append", help="Run ID to delete (can specify multiple)")
    p_delete.add_argument("--dry-run", action="store_true", help="Preview deletion without actually deleting")
    p_delete.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()

    args = parser.parse_args(argv)

    if args.cmd == "viewer":
        # Handle remote mode
        idle_timeout = 0  # 0 means disabled
        if args.remote_mode:
            # Remote mode: force 127.0.0.1, disable reload, set log level
            host = "127.0.0.1"
            log_level = args.log_level.lower()
            idle_timeout = args.idle_timeout
            os.environ["RUNICORN_REMOTE_MODE"] = "1"
            print(f"[Remote Mode] Starting viewer on {host}:{args.port}", flush=True)
            print(f"[Remote Mode] Log level: {log_level}", flush=True)
            print(f"[Remote Mode] Storage: {args.storage or 'default'}", flush=True)
            print(f"[Remote Mode] Idle timeout: {idle_timeout}s", flush=True)
        else:
            host = args.host
            log_level = "info"
            os.environ.pop("RUNICORN_REMOTE_MODE", None)
        
        # Pass idle_timeout via env so create_app can pick it up.
        if idle_timeout > 0:
            os.environ["RUNICORN_IDLE_TIMEOUT"] = str(idle_timeout)
        
        # uvicorn can serve factory via --factory style; do it programmatically here
        app = lambda: create_app(storage=args.storage)  # noqa: E731
        uvicorn.run(
            app, 
            host=host, 
            port=args.port, 
            reload=bool(args.reload) and not args.remote_mode,  # Disable reload in remote mode
            factory=True,
            log_level=log_level
        )
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
        return handle_export(
            args,
            default_storage_dir=_default_storage_dir,
            iter_all_runs_fn=iter_all_runs,
        )

    if args.cmd == "import":
        return handle_import(
            args,
            default_storage_dir=_default_storage_dir,
        )

    if args.cmd == "export-data":
        root = _default_storage_dir(getattr(args, "storage", None))
        run_id = args.run_id
        format = args.format
        output = args.output
        
        # Find run directory (searches both new and legacy layouts)
        entry = find_run_dir_by_id(root, run_id)
        run_dir = entry.dir if entry else None
        
        if not run_dir:
            print(f"Run {run_id} not found")
            return 1
        
        try:
            from .extensions.exporters import MetricsExporter
            exporter = MetricsExporter(run_dir)
            
            if format == "csv":
                if output:
                    exporter.to_csv(Path(output))
                    print(f"Exported to {output}")
                else:
                    content = exporter.to_csv()
                    if content:
                        print(content)
            elif format == "excel":
                output = output or f"{run_id}_metrics.xlsx"
                exporter.to_excel(Path(output))
                print(f"Exported to {output}")
            elif format in ["markdown", "html"]:
                output = output or f"{run_id}_report.{format}"
                exporter.generate_report(Path(output), format)
                print(f"Report generated: {output}")
            
            return 0
        except Exception as e:
            print(f"Export failed: {e}")
            return 1
    
    if args.cmd == "manage":
        from .extensions.experiment import ExperimentManager

        return handle_manage(
            args,
            default_storage_dir=_default_storage_dir,
            experiment_manager_cls=ExperimentManager,
        )
    
    if args.cmd == "rate-limit":
        from .config import get_rate_limit_config, save_rate_limit_config

        return handle_rate_limit(
            args,
            get_rate_limit_config=get_rate_limit_config,
            save_rate_limit_config=save_rate_limit_config,
        )

    if args.cmd == "delete":
        from .assets.cleanup import delete_run_completely

        return handle_delete(
            args,
            default_storage_dir=_default_storage_dir,
            delete_run_completely_fn=delete_run_completely,
            format_bytes_fn=_format_bytes,
        )
    
    parser.print_help()
    return 1


def _format_bytes(size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


if __name__ == "__main__":
    raise SystemExit(main())
