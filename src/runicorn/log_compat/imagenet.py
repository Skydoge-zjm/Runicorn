"""
AverageMeter / ProgressMeter compatibility layer for PyTorch ImageNet-style logging.

This module follows the PyTorch examples ImageNet implementation closely while
adding optional Runicorn integration. The design goal is to preserve the
familiar training-loop shape so users can often migrate by only changing the
import line.

Official references:
- https://github.com/pytorch/examples/blob/main/imagenet/main.py
- https://github.com/huggingface/pytorch-image-models/blob/main/timm/utils/metrics.py
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Iterable, List, Optional

_torch = None
_torch_available = False
try:
    import torch
    _torch = torch
    _torch_available = True
except ImportError:
    pass


def _coerce_numeric(value: Any) -> Optional[float]:
    """Convert common scalar-like values to float."""
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


def _get_active_run():
    try:
        from runicorn.sdk import get_active_run
        return get_active_run()
    except Exception:
        return None


class Summary(Enum):
    NONE = 0
    AVERAGE = 1
    SUM = 2
    COUNT = 3


class AverageMeter:
    """Computes and stores the average and current value.

    Supports both the current PyTorch examples signature:

        AverageMeter(name, use_accel, fmt=':f', summary_type=Summary.AVERAGE)

    and the legacy/common copied variant:

        AverageMeter(name, fmt=':f', summary_type=Summary.AVERAGE)
    """

    def __init__(
        self,
        name: str,
        use_accel: bool | str = False,
        fmt: str | Summary = ":f",
        summary_type: Summary = Summary.AVERAGE,
    ) -> None:
        if isinstance(use_accel, str):
            if isinstance(fmt, Summary):
                summary_type = fmt
            fmt = use_accel
            use_accel = False

        self.name = name
        self.use_accel = bool(use_accel)
        self.fmt = str(fmt)
        self.summary_type = summary_type
        self.reset()

    def reset(self) -> None:
        self.val = 0.0
        self.avg = 0.0
        self.sum = 0.0
        self.count = 0

    def update(self, val: Any, n: int = 1) -> None:
        numeric = _coerce_numeric(val)
        if numeric is None:
            raise TypeError(
                f"AverageMeter.update() expected a numeric value for '{self.name}', "
                f"got {type(val).__name__}"
            )
        self.val = numeric
        self.sum += numeric * n
        self.count += n
        self.avg = self.sum / self.count if self.count > 0 else 0.0

    def all_reduce(self) -> None:
        """Synchronize sum/count across distributed processes when available."""
        if not _torch_available:
            return
        try:
            import torch.distributed as dist

            if not dist.is_available() or not dist.is_initialized():
                return

            if self.use_accel and hasattr(_torch, "accelerator"):
                device = _torch.accelerator.current_accelerator()
            elif _torch.cuda.is_available():
                device = _torch.device("cuda")
            else:
                device = _torch.device("cpu")

            total = _torch.tensor(
                [self.sum, self.count],
                dtype=_torch.float32,
                device=device,
            )
            dist.all_reduce(total, dist.ReduceOp.SUM, async_op=False)
            self.sum, reduced_count = total.tolist()
            self.count = int(reduced_count)
            self.avg = self.sum / self.count if self.count > 0 else 0.0
        except Exception:
            pass

    def __str__(self) -> str:
        fmtstr = "{name} {val" + self.fmt + "} ({avg" + self.fmt + "})"
        return fmtstr.format(**self.__dict__)

    def summary(self) -> str:
        if self.summary_type is Summary.NONE:
            return ""
        if self.summary_type is Summary.AVERAGE:
            fmtstr = "{name} {avg:.3f}"
        elif self.summary_type is Summary.SUM:
            fmtstr = "{name} {sum:.3f}"
        elif self.summary_type is Summary.COUNT:
            fmtstr = "{name} {count:.3f}"
        else:
            raise ValueError(f"invalid summary type {self.summary_type!r}")
        return fmtstr.format(**self.__dict__)


class ProgressMeter:
    """Progress meter compatible with the PyTorch ImageNet example."""

    def __init__(
        self,
        num_batches: int,
        meters: Iterable[AverageMeter],
        prefix: str = "",
    ) -> None:
        self.batch_fmtstr = self._get_batch_fmtstr(num_batches)
        self.meters: List[AverageMeter] = list(meters)
        self.prefix = prefix

    def display(self, batch: int) -> None:
        entries = [self.prefix + self.batch_fmtstr.format(batch)]
        entries += [str(meter) for meter in self.meters]
        print("\t".join(entries))
        self._log_to_run()

    def display_summary(self) -> None:
        entries = [" *"]
        entries += [meter.summary() for meter in self.meters]
        print(" ".join(entry for entry in entries if entry))

    def _get_batch_fmtstr(self, num_batches: int) -> str:
        num_digits = len(str(num_batches // 1))
        fmt = "{:" + str(num_digits) + "d}"
        return "[" + fmt + "/" + fmt.format(num_batches) + "]"

    def _log_to_run(self) -> None:
        run = _get_active_run()
        if run is None:
            return

        metrics = {}
        for meter in self.meters:
            if not meter.name:
                continue
            metrics[meter.name] = meter.val

        if metrics:
            try:
                run.log(metrics)
            except Exception:
                pass


ImagenetAverageMeter = AverageMeter
ImagenetProgressMeter = ProgressMeter
ImagenetSummary = Summary
