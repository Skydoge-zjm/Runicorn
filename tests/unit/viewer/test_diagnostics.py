from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from runicorn.viewer.api.diagnostics import router as diagnostics_router
from runicorn.viewer.utils.diagnostics import (
    DiagnosticsLogContext,
    build_diagnostics_context,
)


def _make_app(context: DiagnosticsLogContext) -> FastAPI:
    app = FastAPI()
    app.state.log_context = context
    app.state.shutdown_event = asyncio.Event()
    app.include_router(diagnostics_router, prefix="/api")
    return app


def test_build_local_diagnostics_context_prunes_old_sessions(tmp_path: Path, monkeypatch):
    from runicorn.viewer.utils import diagnostics as module

    log_root = tmp_path / "logs"
    session_dir = log_root / "sessions"
    session_dir.mkdir(parents=True)

    for idx in range(25):
        path = session_dir / f"old-{idx}.log"
        path.write_text(f"old {idx}\n", encoding="utf-8")
        ts = time.time() - (idx * 60)
        os.utime(path, (ts, ts))

    monkeypatch.setattr(module, "LOCAL_LOG_ROOT", log_root)
    monkeypatch.setattr(module, "LOCAL_SESSION_LOG_DIR", session_dir)

    context = build_diagnostics_context(remote_mode=False)

    assert context.global_log_path == log_root / "viewer.log"
    assert context.session_log_path.parent == session_dir
    assert len(list(session_dir.glob("*.log"))) == 20


def test_build_remote_diagnostics_context_uses_session_directory(tmp_path: Path, monkeypatch):
    from runicorn.viewer.utils import diagnostics as module

    remote_root = tmp_path / "tmp" / "runicorn-viewer"
    monkeypatch.setattr(module, "REMOTE_LOG_ROOT", remote_root)
    monkeypatch.setenv("RUNICORN_REMOTE_MODE", "1")
    monkeypatch.setenv("RUNICORN_REMOTE_SESSION_ID", "remote-session-01")
    monkeypatch.delenv("RUNICORN_REMOTE_LOG_DIR", raising=False)
    monkeypatch.delenv("RUNICORN_LOG_FILE", raising=False)

    context = build_diagnostics_context(remote_mode=True)

    assert context.remote_mode is True
    assert context.session_log_path == remote_root / "sessions" / "remote-session-01" / "viewer.log"
    assert context.sources["bootstrap"] == remote_root / "sessions" / "remote-session-01" / "bootstrap.log"


def test_diagnostics_sources_and_tail_endpoint(tmp_path: Path):
    session_log = tmp_path / "session.log"
    session_log.write_text("line one\nline two\n", encoding="utf-8")
    global_log = tmp_path / "viewer.log"
    global_log.write_text("global one\n", encoding="utf-8")

    context = DiagnosticsLogContext(
        app_session_id="app-session-01",
        remote_mode=False,
        global_log_path=global_log,
        session_log_path=session_log,
        sources={"session": session_log, "global": global_log},
        session_dir=tmp_path,
    )

    client = TestClient(_make_app(context))

    response = client.get("/api/diagnostics/sources")
    assert response.status_code == 200
    data = response.json()
    assert data["defaultSource"] == "session"
    assert {source["id"] for source in data["sources"]} == {"session", "global"}

    response = client.get("/api/diagnostics/logs", params={"source": "session", "lines": 1})
    assert response.status_code == 200
    assert response.text == "line two"


def test_diagnostics_logs_websocket_streams_existing_lines(tmp_path: Path):
    session_log = tmp_path / "session.log"
    session_log.write_text("alpha\nbeta\n", encoding="utf-8")
    context = DiagnosticsLogContext(
        app_session_id="app-session-02",
        remote_mode=False,
        global_log_path=None,
        session_log_path=session_log,
        sources={"session": session_log},
        session_dir=tmp_path,
    )

    client = TestClient(_make_app(context))

    with client.websocket_connect("/api/diagnostics/logs/ws?source=session&lines=10") as websocket:
        assert websocket.receive_text() == "alpha"
        assert websocket.receive_text() == "beta"
