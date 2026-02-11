from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from runicorn.rnconfig import loader as rnconfig_loader


def _write_toml(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_rnconfig_merge_user_then_project_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    user_cfg = tmp_path / "user_rnconfig.toml"
    workspace = tmp_path / "ws"

    _write_toml(
        user_cfg,
        """
[x]
value = 1

[a]
  [a.nested]
  b = 1
  c = 2
""".lstrip(),
    )

    _write_toml(
        workspace / "rnconfig.toml",
        """
[x]
value = 9

[a]
  [a.nested]
  c = 3
  d = 4
""".lstrip(),
    )

    monkeypatch.setattr(rnconfig_loader, "get_rnconfig_file_path", lambda: user_cfg)

    merged = rnconfig_loader.load_effective_rnconfig(str(workspace))

    assert merged["x"]["value"] == 9
    assert merged["a"]["nested"]["b"] == 1
    assert merged["a"]["nested"]["c"] == 3
    assert merged["a"]["nested"]["d"] == 4


def test_rnconfig_cache_reload_on_mtime_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    user_cfg = tmp_path / "user_rnconfig.toml"
    workspace = tmp_path / "ws"

    _write_toml(user_cfg, "[x]\nvalue = 1\n")
    proj_cfg = workspace / "rnconfig.toml"
    _write_toml(proj_cfg, "[x]\nvalue = 2\n")

    monkeypatch.setattr(rnconfig_loader, "get_rnconfig_file_path", lambda: user_cfg)

    a = rnconfig_loader.load_effective_rnconfig(str(workspace))
    assert a["x"]["value"] == 2

    _write_toml(proj_cfg, "[x]\nvalue = 3\n")
    new_ts = int(time.time()) + 5
    os.utime(proj_cfg, (new_ts, new_ts))

    b = rnconfig_loader.load_effective_rnconfig(str(workspace))
    assert b["x"]["value"] == 3
