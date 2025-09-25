from __future__ import annotations

import asyncio
import csv
import os
import sys
import time
import subprocess
import threading
import re
import shutil
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# ---- Paths ----
THIS_FILE = Path(__file__).resolve()
ROOT_DIR = THIS_FILE.parents[2]  # project root: .../Common
RUNS_EXP_NAME = "web_exp"
RUNS_ROOT = ROOT_DIR / "runs" / RUNS_EXP_NAME
DEFAULT_CONFIG = ROOT_DIR / "config" / "default" / "config.yaml"
MAIN_ENTRY = ROOT_DIR / "main.py"
LOG_FILE_NAME = f"{RUNS_EXP_NAME}.log"  # matches main.py: f"{exp_name}.log"
FRONTEND_DIST = ROOT_DIR / "web" / "frontend" / "dist"

RUNS_ROOT.mkdir(parents=True, exist_ok=True)

# ---- FastAPI app ----
app = FastAPI(title="Training Web API", version="0.1.0")

# CORS: allow local dev frontends (Vite default: 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve production frontend (if built) without affecting /api routes
if FRONTEND_DIST.exists():
    # Assets under /assets/*
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


class StartRunRequest(BaseModel):
    # Training arguments (subset; all optional overrides)
    model: Optional[str] = None
    dataset: Optional[str] = None
    epochs: Optional[int] = None
    batch_size: Optional[int] = Field(None, alias="batchSize")
    lr: Optional[float] = None
    num_workers: Optional[int] = Field(None, alias="numWorkers")
    data_root: Optional[str] = Field(None, alias="dataRoot")
    seed: Optional[int] = None

    # Modes / paths
    mode: Optional[str] = None
    pretrained_path: Optional[str] = Field(None, alias="pretrainedPath")
    checkpoint_path: Optional[str] = Field(None, alias="checkpointPath")

    # Feature toggles
    amp: Optional[bool] = None
    save_each_epoch: Optional[bool] = Field(None, alias="saveEachEpoch")
    new_thread_test: Optional[bool] = Field(None, alias="newThreadTest")

    # Advanced
    monitor: Optional[str] = None
    monitor_mode: Optional[str] = Field(None, alias="monitorMode")
    topk_keep: Optional[int] = Field(None, alias="topkKeep")

    # Which Python to launch training with (Windows users may keep default 'python')
    python_exec: Optional[str] = Field(None, alias="pythonExec", description="Python executable for training, default: 'python'")


class StartRunResponse(BaseModel):
    id: str
    pid: int
    run_dir: Optional[str]
    logs_path: Optional[str]
    metrics_path: Optional[str]
    cmd: List[str]


@dataclass
class RunProc:
    pid: int
    popen: subprocess.Popen
    run_dir: Optional[Path]
    created_ts: float


# In-memory registry of active runs
RUNS: Dict[str, RunProc] = {}
# In-memory per-run progress parsed from tqdm stderr frames
RUN_PROGRESS: Dict[str, dict] = {}


def _is_tqdm_line(s: str) -> bool:
    """Heuristics to detect tqdm progress lines that shouldn't be persisted to logs."""
    try:
        if re.search(r"\d{1,3}%\|", s):
            return True
        if re.search(r"it\/(s|sec)", s, re.IGNORECASE):
            return True
        if re.search(r"ETA|elapsed", s, re.IGNORECASE):
            return True
    except Exception:
        pass
    return False


class _StderrForwarder:
    def __init__(self, popen: subprocess.Popen):
        self.popen = popen
        self._buffer = deque(maxlen=2000)
        self._lock = threading.Lock()
        self._fh = None
        self._closed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._run_id: Optional[str] = None
        self._thread.start()

    def set_target(self, file_path: Path):
        try:
            os.makedirs(file_path.parent, exist_ok=True)
            fh = open(file_path, "a", encoding="utf-8", buffering=1)
            with self._lock:
                self._fh = fh
                while self._buffer:
                    line = self._buffer.popleft()
                    fh.write(line)
                fh.flush()
        except Exception:
            pass

    def set_run_id(self, run_id: str):
        with self._lock:
            self._run_id = run_id

    def _run(self):
        try:
            if self.popen.stderr is None:
                return
            for line in self.popen.stderr:
                # Drop tqdm-like progress frames to avoid bloating log files
                try:
                    if _is_tqdm_line(line):
                        # Parse step/total and percent and stash in memory for API
                        try:
                            step = total = percent = None
                            m_ratio = re.search(r"(\d[\d,]*)\s*/\s*(\d[\d,]*)", line)
                            if m_ratio:
                                step = int(m_ratio.group(1).replace(",", ""))
                                total = int(m_ratio.group(2).replace(",", ""))
                            m_pct = re.search(r"(\d{1,3})%\|", line)
                            if m_pct:
                                percent = int(m_pct.group(1))
                            elif step is not None and total:
                                percent = int(max(0, min(100, round(step * 100.0 / max(1, total)))))
                            phase = "test" if re.search(r"Test", line, re.IGNORECASE) else "train"
                            rid = self._run_id
                            if rid and (step is not None) and total:
                                RUN_PROGRESS[rid] = {
                                    "step": step,
                                    "total": total,
                                    "percent": percent if percent is not None else None,
                                    "phase": phase,
                                    "updated_at": _ts(),
                                }
                        except Exception:
                            pass
                        continue
                except Exception:
                    pass
                # Prefix to distinguish from normal stdout logs
                try:
                    out = f"[stderr] {line}"
                except Exception:
                    out = line
                with self._lock:
                    if self._fh:
                        self._fh.write(out)
                        self._fh.flush()
                    else:
                        self._buffer.append(out)
        except Exception:
            pass
        finally:
            with self._lock:
                if self._fh:
                    try:
                        self._fh.flush()
                        self._fh.close()
                    except Exception:
                        pass
                self._closed = True


def _ts() -> float:
    return time.time()


def _list_run_dirs() -> List[Path]:
    if not RUNS_ROOT.exists():
        return []
    return sorted([p for p in RUNS_ROOT.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)


def _discover_new_run_dir(before: List[Path], timeout_s: float = 30.0) -> Optional[Path]:
    before_set = {p.name for p in before}
    deadline = _ts() + timeout_s
    while _ts() < deadline:
        current = _list_run_dirs()
        for p in reversed(current):  # newest first
            if p.name not in before_set:
                return p
        time.sleep(0.5)
    return None


def _build_cli_from_request(req: StartRunRequest) -> List[str]:
    # Always start from default config for sane defaults
    py = req.python_exec or ("python" if os.name == 'nt' else "python3")
    cli: List[str] = [
        py,
        "-X", "utf8",
        str(MAIN_ENTRY),
        "--config", str(DEFAULT_CONFIG),
        "--save-dir", str(RUNS_ROOT),  # exp_name = basename(save_dir) = 'web_exp'
    ]

    def add(flag: str, val: Optional[object]):
        if val is None:
            return
        # Convert pythonic flag name to CLI form (snake->kebab)
        if not flag.startswith("--"):
            flag = "--" + flag.replace("_", "-")
        # For boolean store_true flags in argparse, only include the flag when True
        if isinstance(val, bool):
            if val:
                cli.append(flag)
            return
        cli.append(flag)
        cli.append(str(val))

    add("model", req.model)
    add("dataset", req.dataset)
    add("epochs", req.epochs)
    add("batch_size", req.batch_size)
    add("lr", req.lr)
    add("num_workers", req.num_workers)
    add("data_root", req.data_root)
    add("seed", req.seed)

    add("mode", req.mode)
    add("pretrained_path", req.pretrained_path)
    add("checkpoint_path", req.checkpoint_path)

    add("amp", req.amp)
    add("save_each_epoch", req.save_each_epoch)
    add("new_thread_test", req.new_thread_test)

    add("monitor", req.monitor)
    add("monitor_mode", req.monitor_mode)
    add("topk_keep", req.topk_keep)

    return cli


@app.get("/api/health")
async def health():
    return {"status": "ok", "cwd": str(ROOT_DIR)}


@app.post("/api/runs/start", response_model=StartRunResponse)
async def start_run(req: StartRunRequest):
    if not MAIN_ENTRY.exists():
        raise HTTPException(status_code=500, detail=f"main.py not found at {MAIN_ENTRY}")
    before = _list_run_dirs()
    cmd = _build_cli_from_request(req)
    # Launch training as a subprocess, cwd at project root
    # Ensure UTF-8 std streams in the child to avoid UnicodeEncodeError on Windows (e.g., emoji prints)
    child_env = os.environ.copy()
    # Force UTF-8 mode and ensure stdout/stderr never crash on emojis or non-GBK chars
    child_env["PYTHONIOENCODING"] = "utf-8:backslashreplace"  # encoding[:errors]
    child_env["PYTHONUTF8"] = "1"

    popen = subprocess.Popen(
        cmd,
        cwd=str(ROOT_DIR),
        stdout=subprocess.DEVNULL,  # logging handled by FileLogger in main.py
        stderr=subprocess.PIPE,     # capture stderr to forward into log file
        shell=False,
        text=True,
        bufsize=1,
        encoding="utf-8",
        env=child_env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
    )
    # Start background forwarder for stderr immediately to avoid pipe blocking
    stderr_forwarder = _StderrForwarder(popen)
    # Attach a provisional run_id based on PID to capture very-early tqdm frames
    provisional_id = str(popen.pid)
    try:
        stderr_forwarder.set_run_id(provisional_id)
    except Exception:
        pass
    # Try to find its run_dir by observing new folder under runs/web_exp
    run_dir = _discover_new_run_dir(before, timeout_s=30.0)
    run_id = run_dir.name if run_dir else provisional_id
    # Inform forwarder of final run id for in-memory progress map
    try:
        # migrate stored progress if key changed
        if run_id != provisional_id and RUN_PROGRESS.get(provisional_id):
            RUN_PROGRESS[run_id] = RUN_PROGRESS.pop(provisional_id)
        stderr_forwarder.set_run_id(run_id)
    except Exception:
        pass
    # Once run_dir exists, forward stderr to the actual log file
    if run_dir:
        stderr_forwarder.set_target(run_dir / "log_files" / LOG_FILE_NAME)
    RUNS[run_id] = RunProc(pid=popen.pid, popen=popen, run_dir=run_dir, created_ts=_ts())

    logs_path = str(run_dir / "log_files" / LOG_FILE_NAME) if run_dir else None
    metrics_path = str(run_dir / "log_files" / "metrics.csv") if run_dir else None
    return StartRunResponse(id=run_id, pid=popen.pid, run_dir=str(run_dir) if run_dir else None, logs_path=logs_path, metrics_path=metrics_path, cmd=cmd)


class RunListItem(BaseModel):
    id: str
    run_dir: Optional[str]
    created_time: Optional[float]
    status: str
    pid: Optional[int]
    best_metric_value: Optional[float] = None
    best_metric_name: Optional[str] = None


@app.get("/api/runs", response_model=List[RunListItem])
async def list_runs():
    items: List[RunListItem] = []
    # From filesystem
    for d in _list_run_dirs():
        rid = d.name
        rec = RUNS.get(rid)
        status = "running" if rec and (rec.popen.poll() is None) else "finished"
        # Note: This training backend should not implement hardcoded metric extraction
        # Best metrics should be handled by the unified system through summary.json
        items.append(RunListItem(id=rid, run_dir=str(d), created_time=d.stat().st_mtime, status=status, pid=rec.pid if rec else None, best_metric_value=None, best_metric_name=None))
    # Also include still-running processes that haven't created a run_dir yet
    for rid, rec in RUNS.items():
        if rec.run_dir is None:
            status = "running" if rec.popen.poll() is None else "finished"
            items.append(RunListItem(id=rid, run_dir=None, created_time=rec.created_ts, status=status, pid=rec.pid, best_metric_value=None, best_metric_name=None))
    # Sort newest first
    items.sort(key=lambda x: x.created_time or 0, reverse=True)
    return items


@app.get("/api/runs/{run_id}")
async def run_detail(run_id: str):
    # Resolve run directory
    d = RUNS_ROOT / run_id
    if not d.exists():
        # may be a pid-only run
        rec = RUNS.get(run_id)
        if rec and rec.run_dir is None:
            return {"id": run_id, "status": "running", "pid": rec.pid, "run_dir": None}
        raise HTTPException(status_code=404, detail="run not found")
    rec = RUNS.get(run_id)
    status = "running" if rec and (rec.popen.poll() is None) else "finished"
    return {
        "id": run_id,
        "status": status,
        "pid": rec.pid if rec else None,
        "run_dir": str(d),
        "logs": str(d / "log_files" / LOG_FILE_NAME),
        "metrics": str(d / "log_files" / "metrics.csv"),
        "metrics_step": str(d / "log_files" / "metrics_step.csv"),
    }


@app.get("/api/runs/{run_id}/metrics")
async def get_metrics(run_id: str):
    d = RUNS_ROOT / run_id
    metrics = d / "log_files" / "metrics.csv"
    if not metrics.exists():
        return {"columns": [], "rows": []}
    rows: List[dict] = []
    with open(metrics, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        for row in reader:
            rows.append(row)
    return {"columns": columns, "rows": rows}


@app.get("/api/runs/{run_id}/metrics_step")
async def get_metrics_step(run_id: str):
    d = RUNS_ROOT / run_id
    metrics = d / "log_files" / "metrics_step.csv"
    if not metrics.exists():
        return {"columns": [], "rows": []}
    rows: List[dict] = []
    with open(metrics, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        for row in reader:
            rows.append(row)
    return {"columns": columns, "rows": rows}


@app.post("/api/runs/{run_id}/stop")
async def stop_run(run_id: str):
    rec = RUNS.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found in registry (may have finished)")
    if rec.popen.poll() is None:
        try:
            if os.name == 'nt':
                rec.popen.terminate()
            else:
                rec.popen.terminate()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to terminate: {e}")
    return {"ok": True}


@app.get("/api/runs/{run_id}/progress")
async def get_progress(run_id: str):
    """Return latest parsed tqdm progress for a run.

    Example:
    {
      "available": true,
      "status": "running",
      "phase": "train",
      "step": 123,
      "total": 391,
      "percent": 31,
      "updated_at": 1725180000.123
    }
    """
    prog = RUN_PROGRESS.get(run_id)
    rec = RUNS.get(run_id)
    status = "running" if rec and (rec.popen.poll() is None) else "finished"
    if not prog:
        return {"available": False, "status": status}
    # Shallow copy to avoid mutation
    data = dict(prog)
    data.update({"available": True, "status": status})
    return data


@app.websocket("/api/runs/{run_id}/logs/ws")
async def logs_ws(websocket: WebSocket, run_id: str):
    await websocket.accept()
    d = RUNS_ROOT / run_id
    log_file = d / "log_files" / LOG_FILE_NAME
    if not log_file.exists():
        # If not exists yet, wait shortly for creation
        deadline = _ts() + 15
        while _ts() < deadline and not log_file.exists():
            await asyncio.sleep(0.5)
    if not log_file.exists():
        await websocket.send_text("[error] log file not found")
        await websocket.close()
        return

    try:
        # Tail the file
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
        except Exception:
            pass
        finally:
            await websocket.close()


# ---- GPU Telemetry (via nvidia-smi) ----
def _which_nvidia_smi() -> Optional[str]:
    try:
        found = shutil.which("nvidia-smi")
        if found:
            return found
        # Windows common locations
        if os.name == 'nt':
            candidates = [
                r"C:\\Windows\\System32\\nvidia-smi.exe",
                r"C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
            ]
            for p in candidates:
                if os.path.exists(p):
                    return p
        return None
    except Exception:
        return None


def _to_float(val: str) -> Optional[float]:
    try:
        x = val.strip()
        if not x or x.upper() == 'N/A':
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
        out = subprocess.check_output(cmd, text=True, encoding="utf-8", stderr=subprocess.STDOUT)
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        gpus: List[dict] = []
        for ln in lines:
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) != len(fields):
                # tolerate commas in names by best-effort rebuild
                # assume first two fields are index, name; rest align from the end
                if len(parts) > len(fields):
                    idx = parts[0]
                    name = ",".join(parts[1: len(parts) - (len(fields) - 2)])
                    tail = parts[len(parts) - (len(fields) - 2):]
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
            # add derived fields
            try:
                if d.get("mem_total_mib") and d.get("mem_used_mib") is not None:
                    d["mem_used_pct"] = max(0.0, min(100.0, (d["mem_used_mib"] or 0.0) * 100.0 / max(1.0, d["mem_total_mib"])) )
            except Exception:
                pass
            gpus.append(d)
        return {"available": True, "ts": _ts(), "gpus": gpus}
    except subprocess.CalledProcessError as e:
        return {"available": False, "reason": f"nvidia-smi error: {e.returncode}", "output": e.output}
    except Exception as e:
        return {"available": False, "reason": str(e)}


@app.get("/api/gpu/telemetry")
async def gpu_telemetry():
    return _read_gpu_telemetry()


# ---- Frontend SPA fallback (serve built frontend) ----
if FRONTEND_DIST.exists():
    @app.get("/")
    async def _index_root():
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="index.html not found")

    @app.get("/{full_path:path}")
    async def _spa_catch_all(full_path: str):
        # Let /api/* be handled by API routes
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")
        # Serve file directly if it exists (e.g., favicon.ico)
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Fallback to SPA index
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="index.html not found")
