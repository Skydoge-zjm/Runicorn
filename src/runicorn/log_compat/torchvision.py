"""
MetricLogger compatibility layer for torchvision/DeiT style logging.

This module provides drop-in replacements for torchvision's MetricLogger
and SmoothedValue classes, with automatic Runicorn integration.

Features:
- Pure Python implementation (works without PyTorch)
- Optional PyTorch acceleration when available
- Automatic metric logging to Runicorn via run.log()
- Distributed training support via synchronize_between_processes()

Usage:
    # Replace torchvision import
    # from torchvision.references.detection.utils import MetricLogger
    from runicorn.log_compat.torchvision import MetricLogger
    
    metric_logger = MetricLogger(delimiter="  ")
    for data in metric_logger.log_every(dataloader, 10, header="Train"):
        loss = model(data)
        metric_logger.update(loss=loss.item())

Validates: Requirements 4.1-4.9
"""
from __future__ import annotations

import datetime
import time
import warnings
from collections import defaultdict, deque
from typing import Any, Dict, Iterable, Optional

# Optional torch import with fallback
_torch = None
_torch_available = False
try:
    import torch
    _torch = torch
    _torch_available = True
except ImportError:
    pass


class SmoothedValue:
    """
    Track a series of values and provide access to smoothed values.
    
    Fully compatible with torchvision implementation.
    Works with or without PyTorch installed.
    
    Args:
        window_size: Size of the sliding window for smoothing
        fmt: Format string for __str__ output
    
    Properties:
        median: Median of values in window
        avg: Mean of values in window
        global_avg: Global average across all updates
        max: Maximum value in window
        value: Most recent value
    """
    
    def __init__(self, window_size: int = 20, fmt: Optional[str] = None) -> None:
        if fmt is None:
            fmt = "{median:.4f} ({global_avg:.4f})"
        self.deque: deque = deque(maxlen=window_size)
        self.total = 0.0
        self.count = 0
        self.fmt = fmt
    
    def update(self, value: float, n: int = 1) -> None:
        """
        Add a new value to the series.
        
        Args:
            value: The value to add
            n: Number of times to count this value (for weighted averaging)
        """
        self.deque.append(value)
        self.count += n
        self.total += value * n
    
    @property
    def median(self) -> float:
        """Return median of values in window."""
        if not self.deque:
            return 0.0
        if _torch_available:
            d = _torch.tensor(list(self.deque))
            return d.median().item()
        else:
            # Pure Python fallback
            sorted_values = sorted(self.deque)
            n = len(sorted_values)
            mid = n // 2
            if n % 2 == 0:
                return (sorted_values[mid - 1] + sorted_values[mid]) / 2
            return sorted_values[mid]
    
    @property
    def avg(self) -> float:
        """Return mean of values in window."""
        if not self.deque:
            return 0.0
        if _torch_available:
            d = _torch.tensor(list(self.deque), dtype=_torch.float32)
            return d.mean().item()
        else:
            return sum(self.deque) / len(self.deque)
    
    @property
    def global_avg(self) -> float:
        """Return global average across all updates."""
        return self.total / self.count if self.count > 0 else 0.0
    
    @property
    def max(self) -> float:
        """Return maximum value in window."""
        return max(self.deque) if self.deque else 0.0
    
    @property
    def value(self) -> float:
        """Return most recent value."""
        return self.deque[-1] if self.deque else 0.0
    
    def synchronize_between_processes(self) -> None:
        """
        Synchronize across distributed processes.
        
        No-op if torch.distributed is not available or not initialized.
        Warning: does not synchronize the deque!
        """
        if not _torch_available:
            return
        
        try:
            import torch.distributed as dist
            if not dist.is_available() or not dist.is_initialized():
                return
            
            t = _torch.tensor([self.count, self.total], dtype=_torch.float64, device="cuda")
            dist.barrier()
            dist.all_reduce(t)
            t = t.tolist()
            self.count = int(t[0])
            self.total = t[1]
        except Exception:
            # Silently ignore distributed sync errors
            pass
    
    def __str__(self) -> str:
        return self.fmt.format(
            median=self.median,
            avg=self.avg,
            global_avg=self.global_avg,
            max=self.max,
            value=self.value,
        )


class MetricLogger:
    """
    MetricLogger compatible with torchvision/DeiT style.
    
    Additionally integrates with Runicorn for automatic metric logging.
    When an active Runicorn Run exists, update() calls will automatically
    log metrics via run.log().
    
    Usage:
        from runicorn.log_compat.torchvision import MetricLogger
        # or: from runicorn.log_compat import TorchvisionMetricLogger as MetricLogger
        
        metric_logger = MetricLogger(delimiter="  ")
        for data in metric_logger.log_every(dataloader, 10, header="Train"):
            loss = model(data)
            metric_logger.update(loss=loss.item())
    
    Args:
        delimiter: String to separate metrics in string output
    """
    
    def __init__(self, delimiter: str = "\t") -> None:
        self.meters: Dict[str, SmoothedValue] = defaultdict(SmoothedValue)
        self.delimiter = delimiter
    
    def update(self, **kwargs: Any) -> None:
        """
        Update meters and log to Runicorn if active.
        
        Args:
            **kwargs: Metric name-value pairs. Values can be float, int, or torch.Tensor.
        """
        metrics_to_log: Dict[str, float] = {}
        
        for k, v in kwargs.items():
            # Handle torch.Tensor
            if _torch_available and isinstance(v, _torch.Tensor):
                v = v.item()
            
            # Validate type with warning instead of assert
            if not isinstance(v, (float, int)):
                warnings.warn(
                    f"MetricLogger.update() received non-numeric value for '{k}': "
                    f"{type(v).__name__}. Skipping this metric.",
                    UserWarning,
                    stacklevel=2
                )
                continue
            
            self.meters[k].update(v)
            metrics_to_log[k] = v
        
        # Log to Runicorn if active run exists
        if metrics_to_log:
            try:
                from runicorn.sdk import get_active_run
                run = get_active_run()
                if run is not None:
                    run.log(metrics_to_log)
            except ImportError:
                pass  # Runicorn not installed, just use as regular MetricLogger
    
    def __getattr__(self, attr: str) -> Any:
        if attr in self.meters:
            return self.meters[attr]
        if attr in self.__dict__:
            return self.__dict__[attr]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{attr}'"
        )
    
    def __str__(self) -> str:
        loss_str = []
        for name, meter in self.meters.items():
            loss_str.append(f"{name}: {str(meter)}")
        return self.delimiter.join(loss_str)
    
    def add_meter(self, name: str, meter: SmoothedValue) -> None:
        """
        Add a custom meter.
        
        Args:
            name: Name of the meter
            meter: SmoothedValue instance
        """
        self.meters[name] = meter
    
    def log_every(
        self,
        iterable: Iterable,
        print_freq: int,
        header: Optional[str] = None,
    ):
        """
        Generator that yields items and prints progress.
        
        Print output will be captured by ConsoleCapture if enabled.
        Uses try-finally to ensure "Total time" is always printed.
        
        Args:
            iterable: Iterable to iterate over
            print_freq: Print progress every N iterations
            header: Header string for progress output
            
        Yields:
            Items from the iterable
        """
        i = 0
        if not header:
            header = ""
        start_time = time.time()
        end = time.time()
        iter_time = SmoothedValue(fmt="{avg:.4f}")
        data_time = SmoothedValue(fmt="{avg:.4f}")
        
        # Try to get length
        try:
            total = len(iterable)  # type: ignore
            space_fmt = ":" + str(len(str(total))) + "d"
        except (TypeError, AttributeError):
            total = None
            space_fmt = ""
        
        log_msg_parts = [
            header,
            "[{0" + space_fmt + "}" + ("/{1}]" if total else "]"),
            "eta: {eta}",
            "{meters}",
            "time: {time}",
            "data: {data}",
        ]
        
        if _torch_available and _torch.cuda.is_available():
            log_msg_parts.append("max mem: {memory:.0f}")
        
        log_msg = self.delimiter.join(log_msg_parts)
        MB = 1024.0 * 1024.0
        
        try:
            for obj in iterable:
                data_time.update(time.time() - end)
                yield obj
                iter_time.update(time.time() - end)
                
                if i % print_freq == 0 or (total and i == total - 1):
                    eta_seconds = iter_time.global_avg * ((total - i) if total else 0)
                    eta_string = str(datetime.timedelta(seconds=int(eta_seconds)))
                    
                    format_args: Dict[str, Any] = {
                        "eta": eta_string,
                        "meters": str(self),
                        "time": str(iter_time),
                        "data": str(data_time),
                    }
                    
                    if _torch_available and _torch.cuda.is_available():
                        format_args["memory"] = _torch.cuda.max_memory_allocated() / MB
                    
                    print(log_msg.format(i, total, **format_args))
                
                i += 1
                end = time.time()
        finally:
            # Always print total time, even if iteration was interrupted
            total_time = time.time() - start_time
            total_time_str = str(datetime.timedelta(seconds=int(total_time)))
            print(
                f"{header} Total time: {total_time_str} "
                f"({total_time / max(i, 1):.4f} s / it)"
            )
    
    def synchronize_between_processes(self) -> None:
        """Synchronize meters across distributed processes."""
        for meter in self.meters.values():
            meter.synchronize_between_processes()


# Alias for import convenience
TorchvisionMetricLogger = MetricLogger
