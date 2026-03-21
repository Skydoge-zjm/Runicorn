"""
Diagnostics log API routes.
"""
from __future__ import annotations

import asyncio
from collections import deque
from pathlib import Path
from typing import Any, Iterable

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

from ..utils.diagnostics import DiagnosticsLogContext, diagnostics_sources_payload, resolve_source_path

router = APIRouter()

DEFAULT_TAIL_LINES = 400
MAX_TAIL_LINES = 5000
POLL_INTERVAL_SECONDS = 0.5


def _get_log_context(app: Any) -> DiagnosticsLogContext:
    context = getattr(app.state, "log_context", None)
    if context is None:
        raise HTTPException(status_code=500, detail="Diagnostics logging is not initialized")
    return context


def _read_all_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _tail_lines(path: Path, lines: int) -> list[str]:
    if not path.exists():
        return []
    buffer: deque[str] = deque(maxlen=lines)
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                buffer.append(line.rstrip("\n"))
    except OSError:
        return []
    return list(buffer)


def _read_new_lines(path: Path, position: int) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    lines: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(position)
            for line in handle:
                lines.append(line.rstrip("\n"))
            position = handle.tell()
    except OSError:
        return [], 0
    return lines, position


@router.get("/diagnostics/sources")
async def get_diagnostics_sources(request: Request) -> dict[str, Any]:
    context = _get_log_context(request.app)
    default_source = "viewer" if context.remote_mode else "session"
    return {
        "remoteMode": context.remote_mode,
        "appSessionId": context.app_session_id,
        "defaultSource": default_source,
        "sources": diagnostics_sources_payload(context),
    }


@router.get("/diagnostics/logs")
async def get_diagnostics_log(
    request: Request,
    source: str = Query(...),
    lines: int = Query(DEFAULT_TAIL_LINES, ge=1, le=MAX_TAIL_LINES),
    download: bool = Query(False),
) -> PlainTextResponse:
    context = _get_log_context(request.app)
    try:
        path = resolve_source_path(context, source)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if download:
        content = await asyncio.to_thread(_read_all_text, path)
    else:
        content = "\n".join(await asyncio.to_thread(_tail_lines, path, lines))

    filename = path.name
    headers = {"Cache-Control": "no-store"}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return PlainTextResponse(content, headers=headers)


@router.websocket("/diagnostics/logs/ws")
async def diagnostics_logs_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        context = _get_log_context(websocket.app)
        source = websocket.query_params.get("source", "")
        try:
            path = resolve_source_path(context, source)
        except KeyError:
            await websocket.send_text(f"[error] Unknown diagnostics source: {source}")
            await websocket.close(code=1008)
            return

        try:
            initial_lines = int(websocket.query_params.get("lines", DEFAULT_TAIL_LINES))
        except ValueError:
            initial_lines = DEFAULT_TAIL_LINES
        initial_lines = max(1, min(initial_lines, MAX_TAIL_LINES))

        shutdown_event = getattr(websocket.app.state, "shutdown_event", None)
        sent_waiting_message = False
        position = 0

        while True:
            if shutdown_event is not None and shutdown_event.is_set():
                break

            if path.exists():
                current_size = path.stat().st_size
                if position == 0 or current_size < position:
                    existing_lines = await asyncio.to_thread(_tail_lines, path, initial_lines)
                    for line in existing_lines:
                        await websocket.send_text(line)
                    position = current_size
                else:
                    new_lines, position = await asyncio.to_thread(_read_new_lines, path, position)
                    for line in new_lines:
                        await websocket.send_text(line)
                sent_waiting_message = False
            else:
                if not sent_waiting_message:
                    await websocket.send_text("[info] Waiting for diagnostics log to be created...")
                    sent_waiting_message = True

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await websocket.send_text(f"[error] {e}")
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
