from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class IgnoreRule:
    pattern: str
    negated: bool
    anchored: bool
    dir_only: bool


class IgnoreMatcher:
    def __init__(self, rules: List[IgnoreRule]) -> None:
        self._rules = rules

    def is_ignored(self, rel_posix: str, is_dir: bool) -> bool:
        ignored: Optional[bool] = None
        parts = [p for p in rel_posix.split("/") if p]

        for rule in self._rules:
            if rule.dir_only and not is_dir:
                continue
            if _match_rule(rule, rel_posix, parts):
                ignored = not rule.negated

        return bool(ignored)


def _match_rule(rule: IgnoreRule, rel_posix: str, parts: List[str]) -> bool:
    pat = rule.pattern
    if rule.anchored:
        return fnmatch.fnmatchcase(rel_posix, pat)

    for i in range(len(parts)):
        sub = "/".join(parts[i:])
        if fnmatch.fnmatchcase(sub, pat):
            return True
    return False


def _parse_ignore_lines(lines: List[str]) -> List[IgnoreRule]:
    out: List[IgnoreRule] = []
    for raw in lines:
        s = raw.strip("\n")
        if not s:
            continue
        if s.lstrip().startswith("#"):
            continue
        neg = s.startswith("!")
        if neg:
            s = s[1:]
        s = s.strip()
        if not s:
            continue
        anchored = s.startswith("/")
        if anchored:
            s = s[1:]
        dir_only = s.endswith("/")
        if dir_only:
            s = s[:-1]
        if not s:
            continue
        out.append(IgnoreRule(pattern=s, negated=neg, anchored=anchored, dir_only=dir_only))
    return out


def load_ignore_matcher(
    root: Path,
    rnignore_name: str = ".rnignore",
    gitignore_name: str = ".gitignore",
    extra_excludes: Optional[List[str]] = None,
) -> IgnoreMatcher:
    rules: List[IgnoreRule] = []

    gitignore = root / gitignore_name
    if gitignore.exists():
        rules.extend(_parse_ignore_lines(gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()))

    rnignore = root / rnignore_name
    if rnignore.exists():
        rules.extend(_parse_ignore_lines(rnignore.read_text(encoding="utf-8", errors="ignore").splitlines()))

    if extra_excludes:
        rules.extend(_parse_ignore_lines(list(extra_excludes)))

    return IgnoreMatcher(rules)


def ensure_rnignore(root: Path, rnignore_name: str = ".rnignore") -> Path:
    path = root / rnignore_name
    if path.exists():
        return path

    content = "\n".join(
        [
            ".git/",
            ".venv/",
            "__pycache__/",
            "*.pyc",
            ".idea/",
            "node_modules/",
        ]
    )
    path.write_text(content + "\n", encoding="utf-8")
    return path
