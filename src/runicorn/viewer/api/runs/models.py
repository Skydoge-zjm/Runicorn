from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class RunListItem(BaseModel):
    """Model for run list item response."""

    id: str
    run_dir: Optional[str]
    created_time: Optional[float]
    status: str
    pid: Optional[int] = None
    best_metric_value: Optional[float] = None
    best_metric_name: Optional[str] = None
    path: Optional[str] = None
    alias: Optional[str] = None
    tags: List[str] = []
    assets_count: int = 0


class RunUpdatePayload(BaseModel):
    """Model for run update request."""

    alias: Optional[str] = None
    tags: Optional[List[str]] = None


class MoveRunsPayload(BaseModel):
    """Model for move runs request."""

    run_ids: List[str]
    target_path: str

