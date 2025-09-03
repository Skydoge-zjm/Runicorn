#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate a dummy Runicorn run locally for testing the read-only viewer.

- Writes events.jsonl with step/time metrics and optional stage labels
- Appends human-readable logs to logs.txt (viewable via WS in the UI)
- Updates summary.json with best_val_acc_top1
- Finalizes status.json as finished

Usage:
  python examples/create_test_run.py --total-steps 100 --sleep 0.05 --stages warmup,train,eval

Notes:
- No server is required to generate data; this writes to ./.runicorn by default.
- Start the viewer via `runicorn viewer` or `./run_dev.ps1` to browse the run.
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from pathlib import Path

# Ensure local src/ is importable without installing the package
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from runicorn import sdk as rn  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Create a dummy Runicorn run for testing")
    ap.add_argument("--storage", default=os.environ.get("RUNICORN_DIR") or str(ROOT / ".runicorn"), help="Storage root (default: ./.runicorn)")
    ap.add_argument("--project", default="demo", help="Project name")
    ap.add_argument("--name", default="dummy-run", help="Run name")
    ap.add_argument("--total-steps", dest="total_steps", type=int, default=60, help="Total number of steps to log")
    ap.add_argument("--stages", type=str, default="warmup,train,eval", help="Comma-separated stage labels; stage switches evenly across total steps")
    ap.add_argument("--sleep", type=float, default=0.05, help="Sleep seconds between steps to simulate time")
    return ap.parse_args()


def main() -> int:
    args = parse_args()

    r = rn.init(project=args.project, storage=args.storage, name=args.name)
    print(f"Created run: id={r.id} dir={r.run_dir}")
    r.log_text(f"[info] Starting dummy run '{args.name}' (project={args.project})")

    best = None
    # simple synthetic curves over steps with stage separators
    start_loss = 2.0
    stages = [s.strip() for s in str(getattr(args, "stages", "")).split(",") if s.strip()] or ["train"]
    total_steps = max(1, int(getattr(args, "total_steps", 60)))
    seg_len = max(1, total_steps // len(stages))
    for i in range(1, total_steps + 1):
        stage = stages[min((i - 1) // seg_len, len(stages) - 1)]
        # loss decays with noise
        step_loss = max(0.02, start_loss * math.exp(-0.02 * i) + random.uniform(-0.02, 0.02))
        lr = max(1e-5, 5e-4 * math.exp(-0.001 * i))
        rn.log({
            "train_loss": round(step_loss, 4),
            "lr": round(lr, 6),
        }, stage=stage)
        if args.sleep > 0:
            time.sleep(args.sleep)
        if i % max(1, total_steps // 8) == 0:
            r.log_text(f"step {i:04d}/{total_steps:04d} | stage={stage} | loss {step_loss:.4f}")

        # periodically log a validation metric and update summary
        if (i % seg_len == 0) or (i == total_steps):
            val_acc = min(100.0, 60 + (i / total_steps) * 35 + random.uniform(-1.5, 1.5))
            best = val_acc if best is None else max(best, val_acc)
            rn.log({"val_acc_top1": round(val_acc, 2), "best_val_acc_top1": round(best, 2)}, stage=stage)
            r.summary({"best_val_acc_top1": round(best, 2)})

    r.finish("finished")
    r.log_text("[info] Run finished.")

    print("\nDone. Open the viewer and navigate to the run:")
    print(f"  Storage: {r.storage_root}")
    print(f"  Run ID : {r.id}")
    print(f"  Dir    : {r.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
