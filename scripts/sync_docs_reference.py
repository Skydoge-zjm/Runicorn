from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from runicorn.cli import build_parser  # noqa: E402


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _get_subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise RuntimeError("Runicorn CLI parser does not define subcommands")


def _render_cli_reference() -> str:
    parser = build_parser()
    subparsers = _get_subparsers(parser)
    summaries = {
        action.dest: (action.help or "").strip()
        for action in subparsers._choices_actions
    }

    lines = [
        "# CLI Reference",
        "",
        "This page mirrors the current `runicorn --help` output so the command list,",
        "defaults, and option names stay aligned with the shipped CLI.",
        "",
        "## Commands",
        "",
        "| Command | Purpose |",
        "|---------|---------|",
    ]
    for name, subparser in subparsers.choices.items():
        summary = summaries.get(name) or (subparser.description or "").strip() or "-"
        lines.append(f"| `{name}` | {summary} |")

    lines.extend(
        [
            "",
            "## Top-Level Help",
            "",
            "```text",
            parser.format_help().rstrip(),
            "```",
        ]
    )

    for name, subparser in subparsers.choices.items():
        lines.extend(
            [
                "",
                f"## `{name}`",
                "",
                summaries.get(name) or "No summary available.",
                "",
                "```text",
                subparser.format_help().rstrip(),
                "```",
            ]
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate source-driven CLI reference pages for the user docs site."
    )
    parser.add_argument(
        "--docs-root",
        default=str(ROOT / "docs" / "user-guide" / "docs"),
        help="MkDocs docs/ directory to write generated pages into.",
    )
    args = parser.parse_args()

    docs_root = Path(args.docs_root).resolve()
    _write_text(docs_root / "reference" / "cli-reference.md", _render_cli_reference())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
