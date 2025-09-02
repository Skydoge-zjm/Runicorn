from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import aiofiles
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .sdk import DEFAULT_DIRNAME, _default_storage_dir


# ---------------- Storage helpers ----------------

def _ts() -> float:
    return time.time()


def _storage_root(storage: Optional[str]) -> Path:
    root = _default_storage_dir(storage)
    root.mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(parents=True, exist_ok=True)
    return root


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _list_run_dirs(root: Path) -> List[Path]:
    runs_dir = root / "runs"
    if not runs_dir.exists():
        return []
    return sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)


# ---------------- API schemas ----------------

class RunListItem(BaseModel):
    id: str
    run_dir: Optional[str]
    created_time: Optional[float]
    status: str
    pid: Optional[int] = None
    best_val_acc_top1: Optional[float] = None


# ---------------- Metrics extraction ----------------

def _iter_events(events_path: Path) -> Iterator[Dict[str, Any]]:
    if not events_path.exists():
        return
    try:
        with open(events_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except Exception:
        return


def _aggregate_epoch_metrics(events_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    # Aggregate by epoch: keep last value per key within same epoch
    by_epoch: Dict[int, Dict[str, Any]] = {}
    keys: set[str] = set(["epoch"])  # always include epoch
    for evt in _iter_events(events_path):
        if not isinstance(evt, dict) or evt.get("type") != "metrics":
            continue
        data = evt.get("data") or {}
        if not isinstance(data, dict):
            continue
        epoch_val = data.get("epoch")
        if epoch_val is None:
            continue
        try:
            ep = int(epoch_val)
        except Exception:
            continue
        row = by_epoch.get(ep) or {"epoch": ep}
        for k, v in data.items():
            if k == "epoch":
                continue
            # Only accept JSON-serializable primitives
            if isinstance(v, (int, float, str)) or v is None:
                row[k] = v
                keys.add(k)
        by_epoch[ep] = row
    if not by_epoch:
        return [], []
    cols = ["epoch"] + sorted([k for k in keys if k != "epoch"])  # epoch first
    rows = [by_epoch[e] for e in sorted(by_epoch.keys())]
    # Ensure all rows have all columns
    for r in rows:
        for c in cols:
            r.setdefault(c, None)
    return cols, rows


def _aggregate_step_metrics(events_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    # Use 'global_step' if present; otherwise fall back to 'step'
    rows: List[Dict[str, Any]] = []
    keys: set[str] = set()
    step_key = None
    for evt in _iter_events(events_path):
        if not isinstance(evt, dict) or evt.get("type") != "metrics":
            continue
        data = evt.get("data") or {}
        if not isinstance(data, dict):
            continue
        k = "global_step" if "global_step" in data else ("step" if "step" in data else None)
        if k is None:
            continue
        if step_key is None:
            step_key = k
        try:
            step_val = int(data[k])
        except Exception:
            continue
        row: Dict[str, Any] = {"global_step": step_val}  # normalize to global_step
        for kk, vv in data.items():
            if kk in ("global_step", "step"):
                continue
            if isinstance(vv, (int, float, str)) or vv is None:
                row[kk] = vv
                keys.add(kk)
        rows.append(row)
    if not rows:
        return [], []
    rows.sort(key=lambda r: int(r.get("global_step") or 0))
    cols = ["global_step"] + sorted(list(keys))
    for r in rows:
        for c in cols:
            r.setdefault(c, None)
    return cols, rows


# ---------------- GPU telemetry ----------------

def _which_nvidia_smi() -> Optional[str]:
    try:
        found = shutil.which("nvidia-smi")
        if found:
            return found
        if os.name == "nt":
            for p in [
                r"C:\\Windows\\System32\\nvidia-smi.exe",
                r"C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
            ]:
                if os.path.exists(p):
                    return p
        return None
    except Exception:
        return None


def _to_float(val: str) -> Optional[float]:
    try:
        x = val.strip()
        if not x or x.upper() == "N/A":
            return None
        return float(x)
    except Exception:
        return None


def _read_gpu_telemetry() -> dict:
    path = _which_nvidia_smi()
    if not path:
        return {"available": False, "reason": "nvidia-smi not found in PATH"}
    fields = [
        "index","name","utilization.gpu","utilization.memory","memory.total","memory.used",
        "temperature.gpu","power.draw","power.limit","clocks.sm","clocks.mem","pstate","fan.speed",
    ]
    cmd = [path, f"--query-gpu={','.join(fields)}", "--format=csv,noheader,nounits"]
    try:
        out = os.popen(" ".join(cmd)).read()
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        gpus: List[dict] = []
        for ln in lines:
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) != len(fields):
                if len(parts) > len(fields):
                    idx = parts[0]
                    name = ",".join(parts[1 : len(parts) - (len(fields) - 2)])
                    tail = parts[len(parts) - (len(fields) - 2) :]
                    parts = [idx, name] + tail
                else:
                    continue
            d = {
                "index": int(_to_float(parts[0]) or 0),
                "name": parts[1],
                "util_gpu": _to_float(parts[2]),
                "util_mem": _to_float(parts[3]),
                "mem_total_mib": _to_float(parts[4]),
                "mem_used_mib": _to_float(parts[5]),
                "temp_c": _to_float(parts[6]),
                "power_w": _to_float(parts[7]),
                "power_limit_w": _to_float(parts[8]),
                "clock_sm_mhz": _to_float(parts[9]),
                "clock_mem_mhz": _to_float(parts[10]),
                "pstate": parts[11],
                "fan_speed_pct": _to_float(parts[12]),
            }
            try:
                if d.get("mem_total_mib") and d.get("mem_used_mib") is not None:
                    d["mem_used_pct"] = max(0.0, min(100.0, (d["mem_used_mib"] or 0.0) * 100.0 / max(1.0, d["mem_total_mib"])) )
            except Exception:
                pass
            gpus.append(d)
        return {"available": True, "ts": _ts(), "gpus": gpus}
    except Exception as e:
        return {"available": False, "reason": str(e)}


# ---------------- App factory ----------------

def create_app(storage: Optional[str] = None) -> FastAPI:
    root = _storage_root(storage)

    app = FastAPI(title="Runicorn Viewer API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*", "http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "storage": str(root)}

    @app.get("/api/runs", response_model=List[RunListItem])
    async def list_runs():
        items: List[RunListItem] = []
        for d in _list_run_dirs(root):
            rid = d.name
            meta = _read_json(d / "meta.json")
            status = _read_json(d / "status.json")
            summ = _read_json(d / "summary.json")
            created = meta.get("created_at") if isinstance(meta, dict) else None
            if not isinstance(created, (int, float)):
                try:
                    created = d.stat().st_mtime
                except Exception:
                    created = None
            items.append(
                RunListItem(
                    id=rid,
                    run_dir=str(d),
                    created_time=created,
                    status=str((status.get("status") if isinstance(status, dict) else "finished") or "finished"),
                    pid=(meta.get("pid") if isinstance(meta, dict) else None),
                    best_val_acc_top1=(summ.get("best_val_acc_top1") if isinstance(summ, dict) else None),
                )
            )
        return items

    @app.get("/api/runs/{run_id}")
    async def run_detail(run_id: str):
        d = root / "runs" / run_id
        if not d.exists():
            raise HTTPException(status_code=404, detail="run not found")
        meta = _read_json(d / "meta.json")
        status = _read_json(d / "status.json")
        return {
            "id": run_id,
            "status": str((status.get("status") if isinstance(status, dict) else "finished") or "finished"),
            "pid": (meta.get("pid") if isinstance(meta, dict) else None),
            "run_dir": str(d),
            "logs": str(d / "logs.txt"),
            "metrics": str(d / "events.jsonl"),
            "metrics_step": str(d / "events.jsonl"),
        }

    @app.get("/api/runs/{run_id}/metrics")
    async def get_metrics(run_id: str):
        d = root / "runs" / run_id
        events = d / "events.jsonl"
        cols, rows = _aggregate_epoch_metrics(events)
        return {"columns": cols, "rows": rows}

    @app.get("/api/runs/{run_id}/metrics_step")
    async def get_metrics_step(run_id: str):
        d = root / "runs" / run_id
        events = d / "events.jsonl"
        cols, rows = _aggregate_step_metrics(events)
        return {"columns": cols, "rows": rows}

    @app.get("/api/runs/{run_id}/progress")
    async def get_progress(run_id: str):
        # Read-only viewer has no in-memory progress
        # Could estimate from events, but keep simple for MVP
        return {"available": False, "status": "unknown"}

    @app.websocket("/api/runs/{run_id}/logs/ws")
    async def logs_ws(websocket: WebSocket, run_id: str):
        await websocket.accept()
        d = root / "runs" / run_id
        log_file = d / "logs.txt"
        if not log_file.exists():
            await websocket.send_text("[info] logs.txt not found yet")
            await websocket.close()
            return
        try:
            async with aiofiles.open(log_file, mode="r", encoding="utf-8", errors="ignore") as f:
                await f.seek(0, os.SEEK_END)
                while True:
                    line = await f.readline()
                    if line:
                        await websocket.send_text(line.rstrip("\n"))
                    else:
                        await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            return
        except Exception as e:
            try:
                await websocket.send_text(f"[error] {e}")
            finally:
                await websocket.close()

    @app.get("/api/gpu/telemetry")
    async def gpu_telemetry():
        return _read_gpu_telemetry()

    # Optionally serve bundled static frontend (for pip-installed users)
    try:
        ui_dir = Path(__file__).parent / "webui"
        if ui_dir.exists():
            # Mount at root; '/api' routes remain available since they are explicit
            app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="frontend")
    except Exception:
        # Static UI not found or failed to mount; API still works (dev uses Vite)
        pass

    return app
