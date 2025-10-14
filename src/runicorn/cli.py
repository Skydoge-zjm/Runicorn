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
    p_viewer.add_argument("--port", type=int, default=23300, help="Port to bind (default: 23300)")
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
    
    # Artifacts management subcommand
    p_artifacts = sub.add_parser("artifacts", help="Manage artifacts (models, datasets)")
    p_artifacts.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or None, help="Storage root directory")
    p_artifacts.add_argument("--action", choices=["list", "versions", "info", "delete", "stats"], required=True, help="Artifact action")
    p_artifacts.add_argument("--name", help="Artifact name")
    p_artifacts.add_argument("--type", help="Artifact type (model, dataset, config, etc.)")
    p_artifacts.add_argument("--version", type=int, help="Artifact version number")
    p_artifacts.add_argument("--permanent", action="store_true", help="Permanent delete (vs soft delete)")
    
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
    
    if args.cmd == "artifacts":
        try:
            from .artifacts import create_artifact_storage, LineageTracker
        except ImportError:
            print("Error: Artifacts system is not available")
            print("This may be a module loading issue. Check your installation.")
            return 1
        
        import datetime
        root = _default_storage_dir(getattr(args, "storage", None))
        storage = create_artifact_storage(root)
        
        if args.action == "list":
            artifacts = storage.list_artifacts(type=args.type)
            
            if not artifacts:
                print("No artifacts found.")
                return 0
            
            print(f"Found {len(artifacts)} artifact(s):\n")
            print(f"{'Name':<30} {'Type':<10} {'Versions':<10} {'Size':<15} {'Latest':<10}")
            print("-" * 85)
            
            for art in artifacts:
                size_mb = art["size_bytes"] / (1024 * 1024)
                print(f"{art['name']:<30} {art['type']:<10} {art['num_versions']:<10} {size_mb:>10.2f} MB   v{art['latest_version']}")
            
            return 0
        
        elif args.action == "versions":
            if not args.name:
                print("Error: --name is required for 'versions' action")
                return 1
            
            versions = storage.list_versions(args.name, type=args.type)
            
            if not versions:
                print(f"No versions found for artifact: {args.name}")
                return 0
            
            print(f"Versions for {args.name}:\n")
            print(f"{'Version':<10} {'Created':<25} {'Size':<15} {'Files':<8} {'Run'}")
            print("-" * 90)
            
            for v in versions:
                created = datetime.datetime.fromtimestamp(v.created_at).strftime("%Y-%m-%d %H:%M:%S")
                size_mb = v.size_bytes / (1024 * 1024)
                run_id = v.created_by_run[:20] + "..." if len(v.created_by_run) > 20 else v.created_by_run
                print(f"v{v.version:<9} {created:<25} {size_mb:>10.2f} MB   {v.num_files:<8} {run_id}")
            
            return 0
        
        elif args.action == "info":
            if not args.name or args.version is None:
                print("Error: --name and --version are required for 'info' action")
                return 1
            
            try:
                metadata, manifest = storage.load_artifact(args.name, args.type, args.version)
                
                print(f"\nArtifact: {args.name}:v{args.version}")
                print("=" * 60)
                print(f"Type:         {metadata.type}")
                print(f"Status:       {metadata.status}")
                print(f"Created:      {datetime.datetime.fromtimestamp(metadata.created_at).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Created by:   {metadata.created_by_run}")
                print(f"Size:         {metadata.size_bytes / (1024 * 1024):.2f} MB")
                print(f"Files:        {metadata.num_files}")
                print(f"References:   {metadata.num_references}")
                
                if metadata.description:
                    print(f"Description:  {metadata.description}")
                
                if metadata.aliases:
                    print(f"Aliases:      {', '.join(metadata.aliases)}")
                
                if metadata.tags:
                    print(f"Tags:         {', '.join(metadata.tags)}")
                
                if metadata.metadata:
                    print(f"\nMetadata:")
                    for key, value in metadata.metadata.items():
                        print(f"  {key}: {value}")
                
                if manifest.files:
                    print(f"\nFiles ({len(manifest.files)}):")
                    for f in manifest.files[:10]:  # Show first 10
                        print(f"  {f.path} ({f.size / 1024:.1f} KB)")
                    
                    if len(manifest.files) > 10:
                        print(f"  ... and {len(manifest.files) - 10} more files")
                
                return 0
                
            except FileNotFoundError as e:
                print(f"Error: {e}")
                return 1
        
        elif args.action == "delete":
            if not args.name or args.version is None:
                print("Error: --name and --version are required for 'delete' action")
                return 1
            
            confirm = input(f"Delete {args.name}:v{args.version}? [y/N] ")
            if confirm.lower() != 'y':
                print("Cancelled.")
                return 0
            
            try:
                success = storage.delete_artifact_version(
                    args.name,
                    args.type or "model",
                    args.version,
                    soft_delete=not args.permanent
                )
                
                if success:
                    print(f"✅ {'Permanently' if args.permanent else 'Soft'} deleted {args.name}:v{args.version}")
                else:
                    print(f"Failed to delete {args.name}:v{args.version}")
                    return 1
                
                return 0
                
            except Exception as e:
                print(f"Error: {e}")
                return 1
        
        elif args.action == "stats":
            stats = storage.get_storage_stats()
            
            print("\nArtifact Storage Statistics")
            print("=" * 60)
            print(f"Total Artifacts:  {stats['total_artifacts']}")
            print(f"Total Versions:   {stats['total_versions']}")
            print(f"Total Size:       {stats['total_size_bytes'] / (1024**3):.2f} GB")
            print(f"Dedup Enabled:    {stats['dedup_enabled']}")
            
            if stats['dedup_enabled']:
                print(f"\nDeduplication Stats:")
                print(f"  Pool Size:      {stats.get('dedup_pool_size_bytes', 0) / (1024**3):.2f} GB")
                print(f"  Space Saved:    {stats.get('space_saved_bytes', 0) / (1024**3):.2f} GB")
                print(f"  Dedup Ratio:    {stats.get('dedup_ratio', 0) * 100:.1f}%")
            
            if stats.get('by_type'):
                print(f"\nBy Type:")
                for type_name, type_stats in stats['by_type'].items():
                    print(f"  {type_name.capitalize():<10} {type_stats['count']} artifacts, {type_stats['versions']} versions, {type_stats['size_bytes'] / (1024**3):.2f} GB")
            
            return 0
        
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

    if args.cmd == "export-data":
        root = _default_storage_dir(getattr(args, "storage", None))
        run_id = args.run_id
        format = args.format
        output = args.output
        
        # Find run directory
        from pathlib import Path
        run_dir = None
        
        # Try new layout
        for proj in root.iterdir():
            if not proj.is_dir() or proj.name in ["runs", "webui"]:
                continue
            for exp in proj.iterdir():
                if not exp.is_dir():
                    continue
                runs_dir = exp / "runs"
                if runs_dir.exists():
                    candidate = runs_dir / run_id
                    if candidate.exists():
                        run_dir = candidate
                        break
            if run_dir:
                break
        
        # Try legacy layout
        if not run_dir:
            legacy = root / "runs" / run_id
            if legacy.exists():
                run_dir = legacy
        
        if not run_dir:
            print(f"Run {run_id} not found")
            return 1
        
        try:
            from .exporters import MetricsExporter
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
        root = _default_storage_dir(getattr(args, "storage", None))
        action = args.action
        
        try:
            from .experiment import ExperimentManager
            manager = ExperimentManager(root)
            
            if action == "tag":
                if not args.run_id:
                    print("--run-id is required for tagging")
                    return 1
                tags = args.tags.split(",") if args.tags else []
                success = manager.tag_experiment(args.run_id, tags)
                print(f"Tagged {args.run_id}: {success}")
            
            elif action == "search":
                tags = args.tags.split(",") if args.tags else None
                results = manager.search_experiments(
                    project=args.project,
                    tags=tags,
                    text=args.text
                )
                print(f"Found {len(results)} experiments:")
                for exp in results:
                    print(f"  - {exp.id}: {exp.project}/{exp.name} [{', '.join(exp.tags)}]")
            
            elif action == "delete":
                if not args.run_id:
                    print("--run-id is required for deletion")
                    return 1
                results = manager.delete_experiments([args.run_id])
                print(f"Deleted: {results}")
            
            elif action == "cleanup":
                to_delete = manager.cleanup_old_experiments(args.days, args.dry_run)
                if args.dry_run:
                    print(f"Would delete {len(to_delete)} old experiments:")
                    for run_id in to_delete:
                        print(f"  - {run_id}")
                else:
                    print(f"Deleted {len(to_delete)} old experiments")
            
            return 0
        except Exception as e:
            print(f"Management failed: {e}")
            return 1
    
    if args.cmd == "rate-limit":
        from .config import get_rate_limit_config, save_rate_limit_config
        import json
        
        action = args.action
        
        if action == "show":
            config = get_rate_limit_config()
            print(json.dumps(config, indent=2))
            return 0
        
        elif action == "list":
            config = get_rate_limit_config()
            
            # Show default
            default = config.get("default", {})
            print("Default:")
            print(f"  {default.get('max_requests', 60)}/{default.get('window_seconds', 60)}s")
            
            # Show endpoints
            endpoints = config.get("endpoints", {})
            if endpoints:
                print("\nEndpoints:")
                for endpoint, endpoint_config in sorted(endpoints.items()):
                    desc = endpoint_config.get('description', '')
                    desc_str = f" - {desc}" if desc else ""
                    burst_str = f" (burst: {endpoint_config.get('burst_size')})" if endpoint_config.get('burst_size') else ""
                    print(f"  {endpoint}: {endpoint_config.get('max_requests')}/{endpoint_config.get('window_seconds')}s{burst_str}{desc_str}")
            else:
                print("\nNo endpoint-specific limits configured.")
            return 0
        
        elif action == "get":
            if not args.endpoint:
                print("Error: --endpoint is required for 'get' action")
                return 1
            
            config = get_rate_limit_config()
            endpoint_config = config.get("endpoints", {}).get(args.endpoint)
            
            if endpoint_config:
                print(f"Endpoint: {args.endpoint}")
                print(f"  Max Requests: {endpoint_config.get('max_requests')}")
                print(f"  Window: {endpoint_config.get('window_seconds')}s")
                print(f"  Burst Size: {endpoint_config.get('burst_size', 'None')}")
                if 'description' in endpoint_config:
                    print(f"  Description: {endpoint_config.get('description')}")
            else:
                # Show default
                default_config = config.get("default", {})
                print(f"Endpoint: {args.endpoint} (using default)")
                print(f"  Max Requests: {default_config.get('max_requests', 60)}")
                print(f"  Window: {default_config.get('window_seconds', 60)}s")
                print(f"  Burst Size: {default_config.get('burst_size', 'None')}")
            return 0
        
        elif action == "set":
            if not args.endpoint or args.max_requests is None:
                print("Error: --endpoint and --max-requests are required for 'set' action")
                return 1
            
            config = get_rate_limit_config()
            
            if "endpoints" not in config:
                config["endpoints"] = {}
            
            endpoint_config = {
                "max_requests": args.max_requests,
                "window_seconds": args.window,
                "burst_size": args.burst
            }
            
            if args.description:
                endpoint_config["description"] = args.description
            
            config["endpoints"][args.endpoint] = endpoint_config
            save_rate_limit_config(config)
            
            print(f"✓ Updated rate limit for {args.endpoint}")
            print(f"  Max Requests: {args.max_requests}/{args.window}s")
            if args.burst:
                print(f"  Burst Size: {args.burst}")
            return 0
        
        elif action == "remove":
            if not args.endpoint:
                print("Error: --endpoint is required for 'remove' action")
                return 1
            
            config = get_rate_limit_config()
            
            if "endpoints" in config and args.endpoint in config["endpoints"]:
                del config["endpoints"][args.endpoint]
                save_rate_limit_config(config)
                print(f"✓ Removed rate limit for {args.endpoint}")
            else:
                print(f"⚠ No specific rate limit found for {args.endpoint}")
            return 0
        
        elif action == "settings":
            config = get_rate_limit_config()
            
            if "settings" not in config:
                config["settings"] = {}
            
            # Update settings based on args
            if args.enable:
                config["settings"]["enable_rate_limiting"] = True
            elif args.disable:
                config["settings"]["enable_rate_limiting"] = False
            
            if args.log_violations:
                config["settings"]["log_violations"] = True
            elif args.no_log_violations:
                config["settings"]["log_violations"] = False
            
            if args.whitelist_localhost:
                config["settings"]["whitelist_localhost"] = True
            elif args.no_whitelist_localhost:
                config["settings"]["whitelist_localhost"] = False
            
            save_rate_limit_config(config)
            
            settings = config["settings"]
            print("✓ Updated settings:")
            print(f"  Rate Limiting: {'Enabled' if settings.get('enable_rate_limiting', True) else 'Disabled'}")
            print(f"  Log Violations: {'Yes' if settings.get('log_violations', True) else 'No'}")
            print(f"  Whitelist Localhost: {'Yes' if settings.get('whitelist_localhost', False) else 'No'}")
            return 0
        
        elif action == "reset":
            confirm = input("Reset to default configuration? [y/N] ")
            if confirm.lower() != 'y':
                print("Cancelled.")
                return 0
            
            default_config = {
                "default": {
                    "max_requests": 60,
                    "window_seconds": 60,
                    "burst_size": None,
                    "description": "Default rate limit for all endpoints"
                },
                "endpoints": {},
                "settings": {
                    "enable_rate_limiting": True,
                    "log_violations": True,
                    "whitelist_localhost": False,
                    "custom_headers": {
                        "rate_limit_header": "X-RateLimit-Limit",
                        "rate_limit_remaining_header": "X-RateLimit-Remaining",
                        "rate_limit_reset_header": "X-RateLimit-Reset"
                    }
                }
            }
            
            save_rate_limit_config(default_config)
            print("✓ Reset to default configuration")
            return 0
        
        elif action == "validate":
            try:
                config = get_rate_limit_config()
                
                # Basic validation
                assert isinstance(config, dict), "Configuration must be a dictionary"
                
                # Check default section
                if "default" in config:
                    default = config["default"]
                    assert isinstance(default.get("max_requests"), int), "max_requests must be an integer"
                    assert isinstance(default.get("window_seconds"), int), "window_seconds must be an integer"
                    assert default.get("max_requests") > 0, "max_requests must be positive"
                    assert default.get("window_seconds") > 0, "window_seconds must be positive"
                
                # Check endpoints
                if "endpoints" in config:
                    endpoints = config["endpoints"]
                    assert isinstance(endpoints, dict), "endpoints must be a dictionary"
                    
                    for endpoint, endpoint_config in endpoints.items():
                        assert endpoint.startswith("/"), f"Endpoint '{endpoint}' must start with /"
                        assert isinstance(endpoint_config.get("max_requests"), int), f"{endpoint}: max_requests must be an integer"
                        assert isinstance(endpoint_config.get("window_seconds"), int), f"{endpoint}: window_seconds must be an integer"
                        assert endpoint_config.get("max_requests") > 0, f"{endpoint}: max_requests must be positive"
                        assert endpoint_config.get("window_seconds") > 0, f"{endpoint}: window_seconds must be positive"
                
                print("✓ Configuration is valid")
                return 0
                
            except AssertionError as e:
                print(f"✗ Configuration error: {e}")
                return 1
            except Exception as e:
                print(f"✗ Failed to validate configuration: {e}")
                return 1
            
        return 0
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
