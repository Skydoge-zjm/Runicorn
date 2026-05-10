from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOT_VERSION_FILE = ROOT / "VERSION.txt"
PACKAGE_VERSION_FILE = ROOT / "src" / "runicorn" / "VERSION.txt"


CURRENT_VERSION_FILES = [
    Path("README.md"),
    Path("README_zh.md"),
    Path("docs/DOCUMENTATION_OVERVIEW.md"),
    Path("docs/README_zh.md"),
    Path("docs/api/en/README.md"),
    Path("docs/api/zh/README.md"),
    Path("docs/api/en/QUICK_REFERENCE.md"),
    Path("docs/api/zh/QUICK_REFERENCE.md"),
    Path("docs/api/en/python_client_api.md"),
    Path("docs/api/zh/python_client_api.md"),
    Path("docs/api/en/paths_api.md"),
    Path("docs/api/zh/paths_api.md"),
    Path("docs/api/en/logging_api.md"),
    Path("docs/api/zh/logging_api.md"),
    Path("docs/api/en/API_INDEX.md"),
    Path("docs/api/zh/API_INDEX.md"),
    Path("docs/api/en/remote_api.md"),
    Path("docs/api/zh/remote_api.md"),
    Path("docs/api/en/REMOTE_API_EXAMPLES.md"),
    Path("docs/api/zh/REMOTE_API_EXAMPLES.md"),
    Path("docs/api/runicorn_api.postman_collection.json"),
    Path("docs/architecture/en/README.md"),
    Path("docs/architecture/zh/README.md"),
    Path("docs/architecture/en/SYSTEM_OVERVIEW.md"),
    Path("docs/architecture/zh/SYSTEM_OVERVIEW.md"),
    Path("docs/architecture/en/SSH_BACKEND_ARCHITECTURE.md"),
    Path("docs/architecture/zh/SSH_BACKEND_ARCHITECTURE.md"),
    Path("docs/architecture/en/REMOTE_VIEWER_ARCHITECTURE.md"),
    Path("docs/architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md"),
    Path("docs/architecture/en/FRONTEND_ARCHITECTURE.md"),
    Path("docs/architecture/zh/FRONTEND_ARCHITECTURE.md"),
    Path("desktop/tauri/README.md"),
    Path("desktop/tauri/README_zh.md"),
    Path("web/frontend/tests/smoke/viewer.spec.ts"),
    Path("web/frontend/tests/smoke/remote.spec.ts"),
    Path("docs/user-guide/docs/index.md"),
    Path("docs/user-guide/docs/reference/troubleshooting.md"),
    Path("docs/user-guide/docs/getting-started/quickstart.md"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update Runicorn's authoritative version source and sync derived files.",
    )
    parser.add_argument("version", help="New version, e.g. 0.7.2")
    parser.add_argument(
        "--release-date",
        default=dt.date.today().isoformat(),
        help="Release date for changelog / release note scaffolding (default: today)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing files",
    )
    return parser.parse_args()


def validate_version(value: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise SystemExit(f"Unsupported version format: {value!r}. Expected MAJOR.MINOR.PATCH.")


def read_current_version() -> str:
    return ROOT_VERSION_FILE.read_text(encoding="utf-8").strip()


def write_text(path: Path, content: str, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would update {path.relative_to(ROOT)}")
        return
    path.write_text(content, encoding="utf-8")


def replace_in_file(path: Path, old: str, new: str, *, dry_run: bool) -> None:
    full_path = ROOT / path
    text = full_path.read_text(encoding="utf-8")
    if old not in text:
        return
    write_text(full_path, text.replace(old, new), dry_run=dry_run)


def update_root_version(new_version: str, *, dry_run: bool) -> None:
    write_text(ROOT_VERSION_FILE, f"{new_version}\n", dry_run=dry_run)
    write_text(PACKAGE_VERSION_FILE, f"{new_version}\n", dry_run=dry_run)


def update_desktop_metadata(old_version: str, new_version: str, *, dry_run: bool) -> None:
    replace_in_file(Path("desktop/tauri/src-tauri/Cargo.toml"), old_version, new_version, dry_run=dry_run)
    replace_in_file(Path("desktop/tauri/src-tauri/tauri.conf.json"), old_version, new_version, dry_run=dry_run)

    cargo_lock = ROOT / "desktop/tauri/src-tauri/Cargo.lock"
    text = cargo_lock.read_text(encoding="utf-8")
    old_block = f'name = "runicorn-desktop"\nversion = "{old_version}"'
    new_block = f'name = "runicorn-desktop"\nversion = "{new_version}"'
    if old_block in text:
        write_text(cargo_lock, text.replace(old_block, new_block), dry_run=dry_run)


def update_current_version_docs(old_version: str, new_version: str, *, dry_run: bool) -> None:
    for relative_path in CURRENT_VERSION_FILES:
        replace_in_file(relative_path, old_version, new_version, dry_run=dry_run)
        replace_in_file(relative_path, f"v{old_version}", f"v{new_version}", dry_run=dry_run)


def ensure_release_notes(version: str, release_date: str, *, dry_run: bool) -> None:
    release_pairs = [
        (
            ROOT / "docs/releases/en/RELEASE_NOTES_v{version}.md".format(version=version),
            f"# Release Notes v{version}\n\n**Release date**: {release_date}\n\n---\n\n## Summary\n\nTBD.\n",
        ),
        (
            ROOT / "docs/releases/zh/RELEASE_NOTES_v{version}.md".format(version=version),
            f"# v{version} 发布说明\n\n**发布日期**: {release_date}\n\n---\n\n## 概览\n\n待补充。\n",
        ),
    ]
    for path, content in release_pairs:
        if path.exists():
            continue
        write_text(path, content, dry_run=dry_run)

    releases_readmes = [
        ROOT / "docs/releases/en/README.md",
        ROOT / "docs/releases/zh/README.md",
    ]
    snippets = {
        releases_readmes[0]: f"- **[RELEASE_NOTES_v{version}.md](RELEASE_NOTES_v{version}.md)** - ⭐ v{version} release notes\n",
        releases_readmes[1]: f"- **[RELEASE_NOTES_v{version}.md](RELEASE_NOTES_v{version}.md)** - ⭐ v{version} 发布说明\n",
    }
    anchors = {
        releases_readmes[0]: "## Available Documents\n\n",
        releases_readmes[1]: "## 可用文档\n\n",
    }
    for path in releases_readmes:
        text = path.read_text(encoding="utf-8")
        snippet = snippets[path]
        if snippet in text:
            continue
        anchor = anchors[path]
        if anchor not in text:
            continue
        write_text(path, text.replace(anchor, anchor + snippet), dry_run=dry_run)


def update_postman_json(version: str, *, dry_run: bool) -> None:
    path = ROOT / "docs/api/runicorn_api.postman_collection.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("info", {}).get("version") == version:
        return
    payload["info"]["version"] = version
    formatted = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_text(path, formatted, dry_run=dry_run)


def update_mkdocs_changelog(version: str, release_date: str, *, dry_run: bool) -> None:
    path = ROOT / "docs/user-guide/docs/reference/changelog.md"
    text = path.read_text(encoding="utf-8")
    badge = f'## <span class="rn-badge">v{version}</span> — {release_date}'
    if badge in text:
        return
    insert_after = "All notable changes to Runicorn.\n\n"
    template = (
        f'{badge}\n\n'
        "### Release notes pending\n\n"
        "- Fill in the shipped changes for this release.\n\n"
        "---\n\n"
    )
    if insert_after in text:
        write_text(path, text.replace(insert_after, insert_after + template), dry_run=dry_run)


def main() -> int:
    args = parse_args()
    validate_version(args.version)

    old_version = read_current_version()
    new_version = args.version
    if old_version == new_version:
        print(f"Version is already {new_version}.")
        return 0

    update_root_version(new_version, dry_run=args.dry_run)
    update_desktop_metadata(old_version, new_version, dry_run=args.dry_run)
    update_current_version_docs(old_version, new_version, dry_run=args.dry_run)
    update_postman_json(new_version, dry_run=args.dry_run)
    ensure_release_notes(new_version, args.release_date, dry_run=args.dry_run)
    update_mkdocs_changelog(new_version, args.release_date, dry_run=args.dry_run)

    print(
        f"{'[dry-run] ' if args.dry_run else ''}"
        f"Bumped version from {old_version} to {new_version}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
