from __future__ import annotations

from pathlib import Path
from typing import Optional


def _find_git_root(start: Path) -> Optional[Path]:
    cur = start
    for p in [cur, *cur.parents]:
        if (p / ".git").exists():
            return p
    return None


def get_workspace_root(workspace_root: Optional[str] = None) -> Path:
    if workspace_root:
        return Path(workspace_root).expanduser().resolve()

    cwd = Path.cwd().resolve()
    git_root = _find_git_root(cwd)
    if git_root is not None:
        return git_root

    return cwd
