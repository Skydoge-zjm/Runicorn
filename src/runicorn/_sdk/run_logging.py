from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


def set_primary_metric(run: Any, metric_name: str, mode: str, *, logger: logging.Logger) -> None:
    if run._finished:
        logger.warning("set_primary_metric called after finish(); ignoring")
        return
    if mode not in ["max", "min"]:
        raise ValueError(f"Mode must be 'max' or 'min', got '{mode}'")

    run._primary_metric_name = metric_name
    run._primary_metric_mode = mode
    run._best_metric_value = None
    run._best_metric_step = None
    logger.info("Set primary metric: %s (mode: %s)", metric_name, mode)


def log_metrics(
    run: Any,
    *,
    data: Optional[Dict[str, Any]],
    step: Optional[int],
    stage: Optional[Any],
    extra_kwargs: Dict[str, Any],
    now_ts,
    metric_record_cls: Any,
    logger: logging.Logger,
) -> None:
    if run._finished:
        logger.warning("Run already finished, ignoring %s call", "log")
        return
    ts = now_ts()
    payload: Dict[str, Any] = {}
    if data:
        payload.update(data)
    if extra_kwargs:
        payload.update(extra_kwargs)

    payload.pop("global_step", None)
    payload.pop("step", None)

    if step is not None:
        try:
            run._global_step = int(step)
        except (ValueError, TypeError) as e:
            logger.warning("Invalid step value '%s': %s, auto-incrementing instead", step, e)
            run._global_step += 1
    else:
        run._global_step += 1

    stage_in_payload = payload.pop("stage", None)
    stage_val = stage if stage is not None else stage_in_payload
    payload["global_step"] = run._global_step
    payload["time"] = ts
    if stage_val is not None:
        payload["stage"] = stage_val

    evt = {"ts": ts, "type": "metrics", "data": payload}
    run._append_jsonl(run._events_path, evt, run._events_lock)

    if run.storage_backend and metric_record_cls is not None:
        try:
            metrics = []
            for metric_name, metric_value in payload.items():
                if metric_name in ("global_step", "time", "stage"):
                    continue
                if isinstance(metric_value, (int, float)):
                    metrics.append(
                        metric_record_cls(
                            experiment_id=run.id,
                            timestamp=ts,
                            metric_name=metric_name,
                            metric_value=metric_value,
                            step=run._global_step,
                            stage=stage_val,
                        )
                    )
            if metrics:
                run.storage_backend.log_metrics(run.id, metrics)
        except Exception as e:
            logger.debug("Failed to log to modern storage: %s", e)

    update_best_metric(run, payload, logger=logger)
    if run.monitor:
        try:
            alerts = run.monitor.check_metrics(payload)
            for alert in alerts:
                run.log_text(alert)
        except Exception as e:
            logger.debug("Monitoring check failed: %s", e)


def log_text(run: Any, text: str, *, logger: logging.Logger) -> None:
    if run._finished:
        logger.warning("Run already finished, ignoring %s call", "log_text")
        return

    timestamp = time.strftime("%H:%M:%S")
    lines = text.split("\n")
    prefixed_lines = [f"{timestamp} | {line}" if line.strip() else "" for line in lines]
    formatted_text = "\n".join(prefixed_lines) + "\n"
    with run._logs_lock:
        with open(run._logs_txt_path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(formatted_text)


def get_logging_handler(run: Any, *, level: int, fmt: Optional[str]):
    from ..console import RunicornLoggingHandler

    return RunicornLoggingHandler(run=run, level=level, fmt=fmt)


def log_image(
    run: Any,
    *,
    key: str,
    image: Any,
    step: Optional[int],
    caption: Optional[str],
    format: str,
    quality: int,
    now_ts,
    has_pil: bool,
    has_numpy: bool,
    image_module: Any,
    logger: logging.Logger,
) -> str:
    if run._finished:
        logger.warning("Run already finished, ignoring %s call", "log_image")
        return ""

    rel_name = f"{int(now_ts() * 1000)}_{uuid.uuid4().hex[:6]}_{key}.{format.lower()}"
    path = run.media_dir / rel_name
    try:
        if has_pil and hasattr(image, "save"):
            image.save(path, format=format.upper(), quality=quality)
        elif has_numpy and hasattr(image, "shape"):
            if not has_pil:
                raise RuntimeError("Pillow is required to save numpy arrays. Install with: pip install pillow")
            img = image_module.fromarray(image)
            img.save(path, format=format.upper(), quality=quality)
        elif isinstance(image, (bytes, bytearray)):
            with open(path, "wb") as f:
                f.write(image)
        else:
            p = Path(str(image))
            if not p.exists():
                raise FileNotFoundError(f"Image file not found: {image}")
            with open(path, "wb") as f:
                f.write(p.read_bytes())
    except Exception as e:
        logger.error("Failed to save image '%s': %s", key, e)
        raise

    evt = {
        "ts": now_ts(),
        "type": "image",
        "data": {"key": key, "path": f"media/{rel_name}", "step": step, "caption": caption},
    }
    run._append_jsonl(run._events_path, evt, run._events_lock)
    return f"media/{rel_name}"


def apply_summary_update(run: Any, update: Dict[str, Any], *, logger: logging.Logger) -> None:
    with run._summary_lock:
        cur: Dict[str, Any] = {}
        if run._summary_path.exists():
            try:
                cur = json.loads(run._summary_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to read summary file: %s, starting fresh", e)
                cur = {}
        cur.update(update or {})
        run._summary_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")

    if run.storage_backend:
        try:
            storage_updates = {}
            for field in (
                "best_metric_value",
                "best_metric_name",
                "best_metric_step",
                "best_metric_mode",
            ):
                if field in update:
                    storage_updates[field] = update[field]
            if storage_updates:
                run.storage_backend.update_experiment(run.id, storage_updates)
        except Exception as e:
            logger.debug("Failed to update summary in modern storage: %s", e)


def summary(run: Any, update: Dict[str, Any], *, logger: logging.Logger) -> None:
    if run._finished:
        logger.warning("Run already finished, ignoring %s call", "summary")
        return
    apply_summary_update(run, update, logger=logger)


def update_best_metric(run: Any, payload: Dict[str, Any], *, logger: logging.Logger) -> None:
    if not run._primary_metric_name or run._primary_metric_name not in payload:
        return

    current_value = payload[run._primary_metric_name]
    if not isinstance(current_value, (int, float)):
        return

    is_new_best = False
    if run._best_metric_value is None:
        is_new_best = True
    elif run._primary_metric_mode == "max" and current_value > run._best_metric_value:
        is_new_best = True
    elif run._primary_metric_mode == "min" and current_value < run._best_metric_value:
        is_new_best = True

    if is_new_best:
        run._best_metric_value = current_value
        run._best_metric_step = payload.get("global_step", payload.get("step"))
        logger.debug("New best %s: %s at step %s", run._primary_metric_name, current_value, run._best_metric_step)
        if run.storage_backend:
            try:
                run.storage_backend.update_experiment(
                    run.id,
                    {
                        "best_metric_value": run._best_metric_value,
                        "best_metric_name": run._primary_metric_name,
                        "best_metric_step": run._best_metric_step,
                        "best_metric_mode": run._primary_metric_mode,
                    },
                )
            except Exception as e:
                logger.debug("Failed to update best metric in modern storage: %s", e)
