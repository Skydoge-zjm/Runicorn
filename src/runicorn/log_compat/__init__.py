"""
Compatibility layer for common ML logging patterns.

This module provides drop-in replacements for popular ML logging utilities
that integrate with Runicorn for automatic metric tracking.

Available modules:
- torchvision: MetricLogger and SmoothedValue compatible with torchvision/DeiT

Usage:
    # Replace torchvision import with runicorn
    # from torchvision.references.detection.utils import MetricLogger
    from runicorn.log_compat.torchvision import MetricLogger
    
    # Use exactly as before - metrics are automatically logged to Runicorn
    metric_logger = MetricLogger(delimiter="  ")
    for data in metric_logger.log_every(dataloader, 10, header="Train"):
        loss = model(data)
        metric_logger.update(loss=loss.item())
"""
from __future__ import annotations

from .torchvision import MetricLogger, SmoothedValue

# Alias for convenience
TorchvisionMetricLogger = MetricLogger

__all__ = [
    "MetricLogger",
    "SmoothedValue",
    "TorchvisionMetricLogger",
]
