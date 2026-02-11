from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import pytest


_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
    )


def pytest_configure(config: pytest.Config) -> None:
    src = str(_SRC_ROOT)
    if src not in sys.path:
        sys.path.insert(0, src)


def pytest_collection_modifyitems(config: pytest.Config, items: List[pytest.Item]) -> None:
    if config.getoption("--run-e2e"):
        return

    skip_e2e = pytest.mark.skip(reason="pass --run-e2e to enable")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)
