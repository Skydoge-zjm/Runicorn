from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

import runicorn.registry as registry


def _write_toml(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_get_config_longest_prefix_and_default_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reg_root = tmp_path / "registry"
    monkeypatch.setattr(registry, "get_registry_dir", lambda: reg_root)

    _write_toml(
        reg_root / "datasets" / "imagenet.toml",
        "value = \"D:/imagenet\"\ntrain = \"D:/imagenet/train\"\n",
    )

    assert registry.get_config("datasets/imagenet") == "D:/imagenet"
    assert registry.get_config("datasets/imagenet/train") == "D:/imagenet/train"


def test_get_config_missing_key_has_actionable_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reg_root = tmp_path / "registry"
    monkeypatch.setattr(registry, "get_registry_dir", lambda: reg_root)

    with pytest.raises(KeyError) as exc:
        registry.get_config("datasets/imagenet")

    msg = str(exc.value)
    assert "Registry key not found" in msg
    assert "Registry root" in msg
    assert "Searched" in msg
    assert "Create:" in msg


def test_get_config_mtime_cache_reload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reg_root = tmp_path / "registry"
    monkeypatch.setattr(registry, "get_registry_dir", lambda: reg_root)

    target = reg_root / "datasets" / "a.toml"
    _write_toml(target, "value = \"A\"\n")

    registry.clear_registry_cache()
    assert registry.get_config("datasets/a") == "A"

    _write_toml(target, "value = \"B\"\n")
    new_ts = int(time.time()) + 5
    os.utime(target, (new_ts, new_ts))

    assert registry.get_config("datasets/a") == "B"


def test_get_config_empty_key_raises_value_error() -> None:
    with pytest.raises(ValueError):
        registry.get_config("")
