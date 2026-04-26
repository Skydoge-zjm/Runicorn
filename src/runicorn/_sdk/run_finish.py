from __future__ import annotations

import gc
import json
import logging
import os
import time as time_module
from typing import Any, Dict


def finish_impl(run: Any, *, status: str, normalize_status, now_ts, active_run_state, logger: logging.Logger) -> None:
    status = normalize_status(status)
    run._finished = True
    run._outputs_watch_stop.set()

    if run._console_capture is not None:
        try:
            run._console_capture.stop()
            logger.debug("Console capture stopped for run %s", run.id)
        except Exception as e:
            logger.debug("Failed to stop console capture: %s", e)
        run._console_capture = None

    run.stop_outputs_watch()

    if run._best_metric_value is not None:
        run._apply_summary_update(
            {
                "best_metric_value": run._best_metric_value,
                "best_metric_name": run._primary_metric_name,
                "best_metric_step": run._best_metric_step,
                "best_metric_mode": run._primary_metric_mode,
            }
        )

    with run._status_lock:
        cur: Dict[str, Any] = {}
        if run._status_path.exists():
            try:
                cur = json.loads(run._status_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to read status file: %s, starting fresh", e)
                cur = {}
        cur.update({"status": status, "ended_at": now_ts()})
        run._status_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")

    if run.storage_backend:
        try:
            run.storage_backend.update_experiment(run.id, {"status": status, "ended_at": now_ts()})
        except Exception as e:
            logger.debug("Failed to update status in modern storage: %s", e)

        try:
            if hasattr(run.storage_backend, "close"):
                run.storage_backend.close()
                run.storage_backend = None
                logger.debug("Closed storage backend connections")
                gc.collect()
                time_module.sleep(0.05)
        except Exception as e:
            logger.debug("Failed to close storage backend: %s", e)

    try:
        os.sync()
    except (AttributeError, OSError):
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.FlushFileBuffers.argtypes = [ctypes.c_void_p]
            kernel32.FlushFileBuffers.restype = ctypes.c_bool
        except Exception:
            pass

    time_module.sleep(0.1)
    with active_run_state["lock"]:
        if active_run_state["get"]() is run:
            active_run_state["set"](None)


def exit_impl(run: Any, exc_type) -> None:
    status = "failed" if exc_type is not None else "finished"
    run.finish(status=status)

