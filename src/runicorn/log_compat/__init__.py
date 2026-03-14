"""
Compatibility layer for common ML logging patterns.

This module provides drop-in replacements for popular ML logging utilities
that integrate with Runicorn for automatic metric tracking.

Available modules:
- torchvision: MetricLogger and SmoothedValue compatible with torchvision/DeiT
- imagenet: AverageMeter and ProgressMeter compatible with PyTorch ImageNet examples
- tensorboard: SummaryWriter compatible with common scalar logging usage
- tensorboardX: SummaryWriter compatible with tensorboardX-style usage

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

from .imagenet import AverageMeter, ProgressMeter, Summary
from .tensorboard import SummaryWriter
from .tensorboardX import SummaryWriter as TensorboardXSummaryWriter
from .torchvision import MetricLogger, SmoothedValue

# Alias for convenience
ImagenetAverageMeter = AverageMeter
ImagenetProgressMeter = ProgressMeter
ImagenetSummary = Summary
TensorboardSummaryWriter = SummaryWriter
TorchvisionMetricLogger = MetricLogger

__all__ = [
    "AverageMeter",
    "ProgressMeter",
    "Summary",
    "SummaryWriter",
    "ImagenetAverageMeter",
    "ImagenetProgressMeter",
    "ImagenetSummary",
    "TensorboardSummaryWriter",
    "TensorboardXSummaryWriter",
    "MetricLogger",
    "SmoothedValue",
    "TorchvisionMetricLogger",
]
