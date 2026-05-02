"""Tests for runicorn.enabled — feature flag and NoOpRun."""
from __future__ import annotations

import inspect

import pytest

from runicorn.enabled import (
    NoOpRun,
    enabled,
    is_enabled,
    reset_enabled,
    set_enabled,
)


# ---------------------------------------------------------------------------
# Cleanup: ensure every test starts with a clean global state
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_enabled():
    reset_enabled()
    yield
    reset_enabled()


# ---------------------------------------------------------------------------
# is_enabled / set_enabled / reset_enabled
# ---------------------------------------------------------------------------

class TestIsEnabled:
    def test_default_enabled(self):
        """Default state (no env, no override) → enabled."""
        assert is_enabled() is True

    def test_disable_via_env(self, monkeypatch: pytest.MonkeyPatch):
        """RUNICORN_ON=0 → disabled."""
        monkeypatch.setenv("RUNICORN_ON", "0")
        assert is_enabled() is False

    def test_enable_via_env(self, monkeypatch: pytest.MonkeyPatch):
        """RUNICORN_ON=1 → still enabled."""
        monkeypatch.setenv("RUNICORN_ON", "1")
        assert is_enabled() is True

    def test_set_enabled_programmatic(self):
        """set_enabled(False) overrides default → disabled."""
        set_enabled(False)
        assert is_enabled() is False
        set_enabled(True)
        assert is_enabled() is True

    def test_reset_enabled(self, monkeypatch: pytest.MonkeyPatch):
        """reset_enabled clears override, falls back to env/default."""
        set_enabled(False)
        assert is_enabled() is False
        reset_enabled()
        assert is_enabled() is True  # no env → default True

    def test_override_takes_priority_over_env(self, monkeypatch: pytest.MonkeyPatch):
        """Programmatic override beats env var."""
        monkeypatch.setenv("RUNICORN_ON", "0")
        set_enabled(True)
        assert is_enabled() is True


# ---------------------------------------------------------------------------
# enabled() context manager
# ---------------------------------------------------------------------------

class TestEnabledContextManager:
    def test_enabled_context_manager(self):
        """Block inside `with enabled(False)` is disabled, outside restored."""
        assert is_enabled() is True
        with enabled(False):
            assert is_enabled() is False
        assert is_enabled() is True

    def test_nested_context_managers(self):
        """Nested contexts restore correctly."""
        with enabled(False):
            with enabled(True):
                assert is_enabled() is True
            assert is_enabled() is False
        assert is_enabled() is True


# ---------------------------------------------------------------------------
# NoOpRun
# ---------------------------------------------------------------------------

class TestNoOpRun:
    def test_noop_run_all_methods_silent(self):
        """Every public method on NoOpRun is callable without side effects."""
        noop = NoOpRun()
        noop.set_primary_metric("loss", mode="min")
        noop.log({"loss": 0.5}, step=1)
        noop.log_text("hello")
        assert noop.log_image("key", b"data") == ""
        noop.log_config(args={"lr": 0.01})
        result = noop.scan_outputs_once()
        assert result == {"scanned": 0, "archived": 0, "changed": 0}
        noop.watch_outputs()
        noop.stop_outputs_watch()
        noop.log_dataset("ds", "/tmp")
        noop.log_pretrained("model")
        noop.summary({"key": "val"})
        noop.finish()

    def test_noop_run_disabled_mode_state_helpers(self):
        """Disabled mode exposes stable helper behavior for common SDK paths."""
        noop = NoOpRun()

        noop.append_event({"kind": "metric", "value": 1})
        noop.update_assets_manifest(lambda current: {**current, "latest": {"name": "artifact"}})
        assert noop.should_stop_output_watch() is False

        noop.request_output_watch_stop()
        assert noop.should_stop_output_watch() is True
        noop.clear_output_watch_stop()
        assert noop.should_stop_output_watch() is False

        marker = object()
        noop.set_output_watch_thread(marker)
        assert noop.get_output_watch_thread() is marker

        noop.record_storage_asset(asset_id="asset-1", role="preview")
        noop.record_storage_asset(id="asset-2", role="dataset")
        assert noop.list_storage_assets() == [
            {"asset_id": "asset-1", "role": "preview"},
            {"id": "asset-2", "role": "dataset"},
        ]
        noop.unlink_storage_asset("asset-1")
        assert noop.list_storage_assets() == [{"id": "asset-2", "role": "dataset"}]

        noop.write_summary_data({"loss": 0.1})
        noop.write_status_data({"status": "running"})
        assert noop.read_summary_data() == {"loss": 0.1}
        assert noop.read_status_data() == {"status": "running"}

        noop.close_storage_backend()
        noop.finish()
        assert noop.should_stop_output_watch() is True

    def test_noop_run_attributes(self):
        """NoOpRun exposes expected attributes."""
        noop = NoOpRun(path="test/path", alias="my-alias")
        assert noop.path == "test/path"
        assert noop.alias == "my-alias"
        assert noop.id == "disabled"

    def test_noop_run_defaults(self):
        """NoOpRun with no arguments uses sensible defaults."""
        noop = NoOpRun()
        assert noop.path == "default"
        assert noop.alias is None
        assert noop.id == "disabled"

    def test_noop_run_methods_match_run_interface(self):
        """NoOpRun has all public methods that Run has (API compatibility).

        We compare the *set of public method names* (excluding dunder).
        This catches API drift where Run gains a method but NoOpRun doesn't.
        """
        from runicorn.sdk import Run

        def _public_methods(cls):
            return {
                name
                for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
                if not name.startswith("_")
            }

        run_methods = _public_methods(Run)
        noop_methods = _public_methods(NoOpRun)

        # NoOpRun should cover all public Run methods
        missing = run_methods - noop_methods
        # Some methods may be Run-only (e.g. get_logging_handler) — allow a known set
        allowed_missing = {"get_logging_handler", "get_active_run"}
        unexpected_missing = missing - allowed_missing
        assert not unexpected_missing, f"NoOpRun is missing methods: {unexpected_missing}"
