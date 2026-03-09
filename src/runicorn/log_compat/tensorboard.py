"""
Minimal SummaryWriter compatibility layer for TensorBoard-style scalar logging.

This module follows the high-frequency PyTorch SummaryWriter API closely for
scalar logging use cases, while routing metrics into Runicorn when an active
run exists. The goal is to support low-friction migration by replacing the
import in common training scripts.

Official reference:
- https://github.com/pytorch/pytorch/blob/main/torch/utils/tensorboard/writer.py
"""
from __future__ import annotations

import os
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional


def _get_active_run():
    try:
        from runicorn.sdk import get_active_run
        return get_active_run()
    except Exception:
        return None


def _coerce_numeric(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    item = getattr(value, "item", None)
    if callable(item):
        try:
            coerced = item()
            if isinstance(coerced, (int, float, bool)):
                return float(coerced)
        except Exception:
            return None
    return None


def _coerce_step(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    item = getattr(value, "item", None)
    if callable(item):
        try:
            coerced = item()
            if isinstance(coerced, (int, bool)):
                return int(coerced)
        except Exception:
            return None
    return None


def _default_log_dir(comment: str) -> str:
    current_time = datetime.now().strftime("%b%d_%H-%M-%S")
    return os.path.join("runs", current_time + "_" + socket.gethostname() + comment)


def _join_tag(main_tag: str, tag: str) -> str:
    if not main_tag:
        return str(tag)
    if not tag:
        return str(main_tag)
    return f"{main_tag}/{tag}"


class SummaryWriter:
    """A minimal TensorBoard SummaryWriter-compatible scalar logger."""

    def __init__(
        self,
        log_dir: Optional[str] = None,
        comment: str = "",
        purge_step: Optional[int] = None,
        max_queue: int = 10,
        flush_secs: int = 120,
        filename_suffix: str = "",
    ) -> None:
        if not log_dir:
            log_dir = _default_log_dir(comment)

        self.log_dir = str(log_dir)
        self.purge_step = purge_step
        self.max_queue = max_queue
        self.flush_secs = flush_secs
        self.filename_suffix = filename_suffix
        self._closed = False

        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

    def get_logdir(self) -> str:
        return self.log_dir

    def add_scalar(
        self,
        tag: str,
        scalar_value: Any,
        global_step: Any = None,
        walltime: Optional[float] = None,
        new_style: bool = False,
        double_precision: bool = False,
    ) -> None:
        del walltime, new_style, double_precision
        self._ensure_open()

        numeric = _coerce_numeric(scalar_value)
        if numeric is None:
            raise TypeError(
                f"SummaryWriter.add_scalar() expected a numeric scalar for '{tag}', "
                f"got {type(scalar_value).__name__}"
            )

        step = _coerce_step(global_step)
        if global_step is not None and step is None:
            raise TypeError(
                f"SummaryWriter.add_scalar() expected an integer-like global_step, "
                f"got {type(global_step).__name__}"
            )

        run = _get_active_run()
        if run is not None:
            run.log({str(tag): numeric}, step=step)

    def add_scalars(
        self,
        main_tag: str,
        tag_scalar_dict: Mapping[str, Any],
        global_step: Any = None,
        walltime: Optional[float] = None,
    ) -> None:
        del walltime
        self._ensure_open()

        if not isinstance(tag_scalar_dict, Mapping):
            raise TypeError("tag_scalar_dict should be a mapping.")

        step = _coerce_step(global_step)
        if global_step is not None and step is None:
            raise TypeError(
                f"SummaryWriter.add_scalars() expected an integer-like global_step, "
                f"got {type(global_step).__name__}"
            )

        metrics = {}
        for tag, scalar_value in tag_scalar_dict.items():
            numeric = _coerce_numeric(scalar_value)
            if numeric is None:
                raise TypeError(
                    f"SummaryWriter.add_scalars() expected numeric values, "
                    f"got {type(scalar_value).__name__} for '{tag}'"
                )
            metrics[_join_tag(str(main_tag), str(tag))] = numeric

        run = _get_active_run()
        if run is not None and metrics:
            run.log(metrics, step=step)

    def flush(self) -> None:
        return

    def close(self) -> None:
        if self._closed:
            return
        self.flush()
        self._closed = True

    def reopen(self) -> None:
        if not self._closed:
            return
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            self.reopen()


TensorboardSummaryWriter = SummaryWriter
