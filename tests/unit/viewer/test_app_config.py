from __future__ import annotations

from fastapi.testclient import TestClient

from runicorn.viewer import _get_cors_settings, create_app


def test_default_cors_settings_cover_local_and_desktop(monkeypatch) -> None:
    monkeypatch.delenv("RUNICORN_CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.delenv("RUNICORN_CORS_ALLOW_ORIGIN_REGEX", raising=False)

    settings = _get_cors_settings(remote_mode=False)

    assert settings["allow_credentials"] is True
    assert settings["allow_origin_regex"]
    assert "tauri://localhost" in settings["allow_origins"]


def test_explicit_cors_settings_override_defaults(monkeypatch) -> None:
    monkeypatch.setenv("RUNICORN_CORS_ALLOW_ORIGINS", "https://viewer.example.com, https://ops.example.com")
    monkeypatch.setenv("RUNICORN_CORS_ALLOW_ORIGIN_REGEX", "^https://preview\\.example\\.com$")

    settings = _get_cors_settings(remote_mode=True)

    assert settings["allow_origins"] == [
        "https://viewer.example.com",
        "https://ops.example.com",
    ]
    assert settings["allow_origin_regex"] == "^https://preview\\.example\\.com$"


def test_lifespan_starts_and_stops_runtime_state() -> None:
    app = create_app()

    with TestClient(app) as client:
        assert client.app.state.status_check_task is not None
        assert client.app.state.session_cleanup_task is not None

    assert client.app.state.status_check_task is None
    assert client.app.state.session_cleanup_task is None
