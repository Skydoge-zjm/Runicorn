#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate a dummy Runicorn run locally for testing the read-only viewer.

- Writes events.jsonl with epoch metrics and optional step metrics (global_step)
- Appends human-readable logs to logs.txt (viewable via WS in the UI)
- Updates summary.json with best_val_acc_top1
- Finalizes status.json as finished

Usage:
  python examples/create_test_run.py --epochs 5 --steps 20 --sleep 0.05

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
    ap.add_argument("--epochs", type=int, default=5, help="Number of epochs")
    ap.add_argument("--steps", type=int, default=20, help="Steps per epoch for step metrics (0 to disable)")
    ap.add_argument("--sleep", type=float, default=0.05, help="Sleep seconds between steps to simulate time")
    return ap.parse_args()


def main() -> int:
    args = parse_args()

    r = rn.init(project=args.project, storage=args.storage, name=args.name)
    print(f"Created run: id={r.id} dir={r.run_dir}")
    r.log_text(f"[info] Starting dummy run '{args.name}' (project={args.project})")

    best = None
    global_step = 0

    # simple synthetic curves
    start_loss = 2.0
    for epoch in range(1, args.epochs + 1):
        # step metrics (optional)
        if args.steps > 0:
            for s in range(args.steps):
                global_step += 1
                # loss decays with noise
                step_loss = max(0.05, start_loss * math.exp(-0.08 * (epoch - 1)) + random.uniform(-0.02, 0.02))
                rn.log({"global_step": global_step, "train_loss": round(step_loss, 4)})
                if args.sleep > 0:
                    time.sleep(args.sleep)
                if s % max(1, args.steps // 5) == 0:
                    r.log_text(f"epoch {epoch:02d} | step {s+1:03d}/{args.steps:03d} | loss {step_loss:.4f} | it/s ~{(1.0/max(args.sleep,1e-3)):.1f}")

        # epoch metrics
        train_loss = max(0.05, start_loss * math.exp(-0.5 * (epoch - 1)) + random.uniform(-0.03, 0.03))
        val_loss = max(0.05, start_loss * math.exp(-0.55 * (epoch - 1)) + random.uniform(-0.04, 0.04))
        train_acc = min(100.0, 60 + (epoch - 1) * 6 + random.uniform(-1.5, 1.5))
        val_acc = min(100.0, 55 + (epoch - 1) * 6.5 + random.uniform(-2.0, 2.0))
        best = val_acc if best is None else max(best, val_acc)

        rn.log({
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "train_acc_top1": round(train_acc, 2),
            "val_acc_top1": round(val_acc, 2),
            "best_val_acc_top1": round(best, 2),
        })
        r.summary({"best_val_acc_top1": round(best, 2)})
        r.log_text(f"[epoch {epoch:02d}] train_loss={train_loss:.4f} val_loss={val_loss:.4f} val_acc={val_acc:.2f}% best={best:.2f}%")

    r.finish("finished")
    r.log_text("[info] Run finished.")

    print("\nDone. Open the viewer and navigate to the run:")
    print(f"  Storage: {r.storage_root}")
    print(f"  Run ID : {r.id}")
    print(f"  Dir    : {r.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
