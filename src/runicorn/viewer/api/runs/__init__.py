"""
Run Management API Routes

Handles CRUD operations for experiment runs, including soft delete and restore functionality.
"""
from __future__ import annotations

from fastapi import APIRouter

from .assets import _download_from_manifest, router as assets_router
from .deletion import router as deletion_router
from .list_detail import router as list_detail_router
from .models import MoveRunsPayload, RunListItem, RunUpdatePayload
from .mutations import router as mutations_router
from .recycle import router as recycle_router
from .shared import _count_assets_from_assets_json

router = APIRouter()
router.include_router(list_detail_router)
router.include_router(mutations_router)
router.include_router(assets_router)
router.include_router(recycle_router)
router.include_router(deletion_router)

__all__ = [
    "MoveRunsPayload",
    "RunListItem",
    "RunUpdatePayload",
    "_count_assets_from_assets_json",
    "_download_from_manifest",
    "router",
]
