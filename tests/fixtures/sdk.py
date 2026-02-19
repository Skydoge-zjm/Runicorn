"""SDK-related fixtures shared across test layers."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def run_instance(storage_root: Path, monkeypatch: pytest.MonkeyPatch):
    """Create a real :class:`Run` backed by *storage_root*.

    Modern storage is force-enabled.  Console capture is disabled for
    deterministic output.  The run is ``finish()``-ed after the test.
    """
    monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    from runicorn.sdk import Run

    run = Run(
        path="test/unit",
        storage=str(storage_root),
        capture_console=False,
    )
    yield run
    try:
        run.finish()
    except Exception:
        pass


@pytest.fixture
def noop_run():
    """Return a ``NoOpRun`` instance."""
    from runicorn.enabled import NoOpRun

    return NoOpRun()
