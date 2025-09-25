#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate a comprehensive Runicorn run showcasing v0.3.0 features.

New Features Demonstrated:
- Universal best metric system with automatic tracking
- Environment capture (Git info, dependencies, system specs)
- Exception handling and status management
- Enhanced logging and monitoring

File Generation:
- events.jsonl with step/time metrics and stage labels
- logs.txt for real-time log viewing via WebSocket
- environment.json with complete environment snapshot
- summary.json with automatically tracked best metrics
- status.json with proper completion status

Usage:
  python examples/create_test_run.py --total-steps 100 --sleep 0.05 --stages warmup,train,eval

Features:
- Automatic best metric tracking (accuracy maximization)
- Simulated training curves with realistic metrics
- Environment capture for reproducibility
- Proper exception handling and status management

Notes:
- No server required; writes to ./.runicorn by default
- Start viewer via `runicorn viewer` to see the enhanced UI
- Try the new recycle bin, settings, and status features
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

    r = rn.init(project=args.project, storage=args.storage, name=args.name, capture_env=True)
    print(f"Created run: id={r.id} dir={r.run_dir}")
    r.log_text(f"[info] Starting enhanced dummy run '{args.name}' (project={args.project})")
    r.log_text(f"[info] Environment captured automatically")
    
    # Set accuracy as the primary metric (to be maximized) - v0.3.0 feature
    rn.set_primary_metric("accuracy", mode="max")
    r.log_text("[info] Set primary metric: accuracy (max) - will be auto-tracked")

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

        # periodically log validation metrics
        if (i % seg_len == 0) or (i == total_steps):
            val_acc = min(100.0, 60 + (i / total_steps) * 35 + random.uniform(-1.5, 1.5))
            best = val_acc if best is None else max(best, val_acc)
            
            # Log accuracy - v0.3.0 auto-tracks best value
            rn.log({
                "accuracy": round(val_acc, 2),
                "validation_loss": round(2.0 * math.exp(-i/30) + random.uniform(-0.1, 0.1), 4),
                "learning_rate": 0.001 * (0.95 ** (i // 10))
            }, stage=stage)
            
            r.log_text(f"[metrics] Step {i}: accuracy={val_acc:.2f}% (best so far: {best:.2f}%)")

    # Add final summary with v0.3.0 enhanced metadata
    r.summary({
        "final_accuracy": round(best, 2),
        "total_steps": total_steps,
        "stages_used": ",".join(stages),
        "notes": f"Enhanced demo run showcasing v0.3.0 features",
        "framework": "demo",
        "model_type": "synthetic"
    })
    
    r.finish("finished")
    r.log_text("[info] Run finished successfully with auto-tracked best metrics.")

    print(f"\n✅ Done! Enhanced run created with v0.3.0 features:")
    print(f"   - Best accuracy: {best:.2f}% (auto-tracked)")
    print(f"   - Environment captured: Git info, dependencies, system specs")
    print(f"   - Status management: Automatic exception handling")
    print(f"\n🌐 Open the viewer to explore new features:")
    print(f"   runicorn viewer")
    print(f"   Then browse to: http://127.0.0.1:8000")
    print(f"\n🎯 Try the new v0.3.0 features:")
    print(f"   - Best Metric column in experiment list")
    print(f"   - Modern tabbed Settings interface")
    print(f"   - Soft delete and Recycle Bin")
    print(f"   - Responsive design on different window sizes")
    print(f"  Storage: {r.storage_root}")
    print(f"  Run ID : {r.id}")
    print(f"  Dir    : {r.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
