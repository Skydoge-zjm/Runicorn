from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def handle_manage(
    args: Any,
    *,
    default_storage_dir: Callable[[str | None], Path],
    experiment_manager_cls: Callable[[Path], Any],
) -> int:
    root = default_storage_dir(getattr(args, "storage", None))
    action = args.action

    try:
        manager = experiment_manager_cls(root)

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
                text=args.text,
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


def handle_delete(
    args: Any,
    *,
    default_storage_dir: Callable[[str | None], Path],
    delete_run_completely_fn: Callable[..., dict[str, Any]],
    format_bytes_fn: Callable[[int], str],
) -> int:
    root = default_storage_dir(getattr(args, "storage", None))
    run_ids = getattr(args, "run_ids", None) or []
    dry_run = getattr(args, "dry_run", False)
    if not run_ids:
        print("Error: --run-id is required")
        print("Usage: runicorn delete --run-id <run_id> [--run-id <run_id2>] [--dry-run] [--force]")
        return 1

    if dry_run:
        print("=" * 60)
        print("DRY RUN - No files will be deleted")
        print("=" * 60)

    total_blobs = 0
    total_bytes = 0

    for run_id in run_ids:
        prefix = "[Preview] " if dry_run else ""
        print(f"\n{prefix}Deleting run: {run_id}")

        result = delete_run_completely_fn(
            run_id=run_id,
            storage_root=root,
            dry_run=dry_run,
        )

        if not result["success"]:
            print(f"  Failed: {result['errors']}")
            continue

        print(f"  Run directory: {'would be deleted' if dry_run else 'deleted'}")

        orphaned = result.get("orphaned_assets", [])
        kept = result.get("kept_assets", [])

        if orphaned:
            print(f"  Orphaned assets ({len(orphaned)}) - {'would be' if dry_run else ''} deleted:")
            for asset in orphaned:
                name = asset.get("name") or (asset.get("fingerprint") or "")[:16] or "unknown"
                print(f"    - [{asset.get('asset_type')}] {name}")

        if kept:
            print(f"  Shared assets ({len(kept)}) - kept (referenced by other runs):")
            for asset in kept:
                name = asset.get("name") or (asset.get("fingerprint") or "")[:16] or "unknown"
                print(f"    - [{asset.get('asset_type')}] {name}")

        blobs = result.get("blobs_deleted", 0)
        bytes_freed = result.get("bytes_freed", 0)
        total_blobs += blobs
        total_bytes += bytes_freed

        if blobs > 0:
            print(f"  Blobs deleted: {blobs} ({format_bytes_fn(bytes_freed)})")

    print("\n" + "=" * 60)
    if dry_run:
        print(f"DRY RUN Summary: Would delete {len(run_ids)} run(s)")
        print(f"  Blobs: {total_blobs}")
        print(f"  Space: {format_bytes_fn(total_bytes)}")
    else:
        print(f"Deleted {len(run_ids)} run(s)")
        print(f"  Blobs removed: {total_blobs}")
        print(f"  Space freed: {format_bytes_fn(total_bytes)}")

    return 0
