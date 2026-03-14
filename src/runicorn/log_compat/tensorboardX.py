"""
tensorboardX SummaryWriter compatibility layer.

This module preserves the high-frequency `tensorboardX.SummaryWriter` calling
style while delegating to Runicorn's TensorBoard-style compat implementation.
The migration goal is:

    from tensorboardX import SummaryWriter

becomes:

    from runicorn.log_compat.tensorboardX import SummaryWriter
"""
from __future__ import annotations

from typing import Any, Optional

from .tensorboard import SummaryWriter as _BaseSummaryWriter


class SummaryWriter(_BaseSummaryWriter):
    """tensorboardX-compatible SummaryWriter wrapper."""

    def __init__(
        self,
        logdir: Optional[str] = None,
        comment: Optional[str] = "",
        purge_step: Optional[int] = None,
        max_queue: Optional[int] = 10,
        flush_secs: Optional[int] = 120,
        filename_suffix: Optional[str] = "",
        write_to_disk: Optional[bool] = True,
        log_dir: Optional[str] = None,
        comet_config: Optional[dict] = None,
        **kwargs: Any,
    ) -> None:
        del write_to_disk, comet_config, kwargs
        resolved_log_dir = log_dir if log_dir is not None else logdir
        super().__init__(
            log_dir=resolved_log_dir,
            comment=comment or "",
            purge_step=purge_step,
            max_queue=max_queue or 10,
            flush_secs=flush_secs or 120,
            filename_suffix=filename_suffix or "",
        )
        self.logdir = self.log_dir

    def add_scalar(
        self,
        tag: str,
        scalar_value: Any,
        global_step: Any = None,
        walltime: Optional[float] = None,
        display_name: Optional[str] = "",
        summary_description: Optional[str] = "",
    ) -> None:
        del display_name, summary_description
        super().add_scalar(
            tag=tag,
            scalar_value=scalar_value,
            global_step=global_step,
            walltime=walltime,
        )

    def add_hparams(
        self,
        hparam_dict: dict[str, Any],
        metric_dict: dict[str, Any],
        name: Optional[str] = None,
        global_step: Any = None,
    ) -> None:
        super().add_hparams(
            hparam_dict=hparam_dict,
            metric_dict=metric_dict,
            run_name=name,
            global_step=global_step,
        )


TensorboardXSummaryWriter = SummaryWriter
