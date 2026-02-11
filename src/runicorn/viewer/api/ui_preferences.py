"""
UI Preferences API

Manages user interface preferences like column widths, table settings, etc.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, Body, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class ColumnWidthPreference(BaseModel):
    """Column width preference for a specific table and window size."""
    table: str
    size: str  # Window size key like "1920x1080"
    widths: Dict[str, int]
    window_width: Optional[int] = None
    window_height: Optional[int] = None


def get_preferences_file() -> Path:
    """Get the UI preferences file path."""
    from ...config import get_config_file_path
    
    config_dir = get_config_file_path().parent
    prefs_file = config_dir / "ui_preferences.json"
    
    return prefs_file


def load_all_preferences() -> Dict[str, Any]:
    """Load all UI preferences from file."""
    prefs_file = get_preferences_file()
    
    if not prefs_file.exists():
        return {"column_widths": {}}
    
    try:
        with open(prefs_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load UI preferences: {e}")
        return {"column_widths": {}}


def save_all_preferences(preferences: Dict[str, Any]) -> None:
    """Save all UI preferences to file."""
    prefs_file = get_preferences_file()
    prefs_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(prefs_file, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save UI preferences: {e}")


@router.get("/config/column-widths")
async def get_column_widths(
    table: str = Query(..., description="Table identifier"),
    size: str = Query(..., description="Window size key")
) -> Dict[str, Any]:
    """
    Get column width preferences for a specific table and window size.
    
    Args:
        table: Table identifier (e.g., 'experiments', 'runs')
        size: Window size key (e.g., '1920x1080')
        
    Returns:
        Column width preferences
    """
    preferences = load_all_preferences()
    column_widths = preferences.get("column_widths", {})
    
    # Build key: table@size
    key = f"{table}@{size}"
    
    widths = column_widths.get(key, {})
    
    return {
        "table": table,
        "size": size,
        "widths": widths.get("widths", {}) if isinstance(widths, dict) else {}
    }


@router.post("/config/column-widths")
async def save_column_widths(
    payload: ColumnWidthPreference = Body(...)
) -> Dict[str, Any]:
    """
    Save column width preferences for a specific table and window size.
    
    Args:
        payload: Column width preference data
        
    Returns:
        Success status
    """
    preferences = load_all_preferences()
    
    if "column_widths" not in preferences:
        preferences["column_widths"] = {}
    
    # Build key: table@size
    key = f"{payload.table}@{payload.size}"
    
    preferences["column_widths"][key] = {
        "widths": payload.widths,
        "window_width": payload.window_width,
        "window_height": payload.window_height,
        "updated_at": __import__('time').time()
    }
    
    save_all_preferences(preferences)
    
    logger.info(f"Saved column width preferences for {key}")
    
    return {
        "ok": True,
        "message": "Column width preferences saved"
    }


@router.delete("/config/column-widths")
async def reset_column_widths(
    table: str = Query(..., description="Table identifier"),
    size: Optional[str] = Query(None, description="Window size key (if None, reset all)")
) -> Dict[str, Any]:
    """
    Reset column width preferences.
    
    Args:
        table: Table identifier
        size: Window size key (optional, if None reset all sizes for this table)
        
    Returns:
        Success status
    """
    preferences = load_all_preferences()
    column_widths = preferences.get("column_widths", {})
    
    if size:
        # Reset specific size
        key = f"{table}@{size}"
        if key in column_widths:
            del column_widths[key]
    else:
        # Reset all sizes for this table
        keys_to_delete = [k for k in column_widths.keys() if k.startswith(f"{table}@")]
        for key in keys_to_delete:
            del column_widths[key]
    
    preferences["column_widths"] = column_widths
    save_all_preferences(preferences)
    
    return {
        "ok": True,
        "message": "Column width preferences reset"
    }


@router.post("/config/column-widths/reset")
async def reset_column_width_preferences(
    table: str = Query(..., description="Table identifier"),
    size: Optional[str] = Query(None, description="Window size key (if None, reset all)")
) -> Dict[str, Any]:
    """
    Reset column width preferences.
    
    Args:
        table: Table identifier
        size: Window size key (if None, reset all)
        
    Returns:
        Success status
    """
    preferences = load_all_preferences()
    column_widths = preferences.get("column_widths", {})
    
    if size:
        # Reset specific size
        key = f"{table}@{size}"
        column_widths.pop(key, None)
    else:
        # Reset all sizes for this table
        keys_to_delete = [k for k in column_widths.keys() if k.startswith(f"{table}@")]
        for key in keys_to_delete:
            del column_widths[key]
    
    preferences["column_widths"] = column_widths
    save_all_preferences(preferences)
    
    return {
        "ok": True,
        "message": "Column width preferences reset"
    }


@router.get("/config/dismissed-alerts")
async def get_dismissed_alerts() -> Dict[str, Any]:
    """
    Get list of dismissed alert IDs.
    
    Returns:
        List of dismissed alert IDs
    """
    preferences = load_all_preferences()
    dismissed_alerts = preferences.get("dismissed_alerts", [])
    
    return {
        "dismissed_alerts": dismissed_alerts
    }


@router.post("/config/dismissed-alerts/dismiss")
async def dismiss_alert(
    alert_id: str = Body(..., embed=True, description="Alert ID to dismiss")
) -> Dict[str, Any]:
    """
    Dismiss an alert (add to dismissed list).
    
    Args:
        alert_id: Alert identifier
        
    Returns:
        Success status
    """
    preferences = load_all_preferences()
    
    if "dismissed_alerts" not in preferences:
        preferences["dismissed_alerts"] = []
    
    if alert_id not in preferences["dismissed_alerts"]:
        preferences["dismissed_alerts"].append(alert_id)
        save_all_preferences(preferences)
        logger.info(f"Dismissed alert: {alert_id}")
    
    return {
        "ok": True,
        "message": f"Alert '{alert_id}' dismissed"
    }


@router.post("/config/dismissed-alerts/undismiss")
async def undismiss_alert(
    alert_id: str = Body(..., embed=True, description="Alert ID to undismiss")
) -> Dict[str, Any]:
    """
    Undismiss an alert (remove from dismissed list).
    
    Args:
        alert_id: Alert identifier
        
    Returns:
        Success status
    """
    preferences = load_all_preferences()
    dismissed_alerts = preferences.get("dismissed_alerts", [])
    
    if alert_id in dismissed_alerts:
        dismissed_alerts.remove(alert_id)
        preferences["dismissed_alerts"] = dismissed_alerts
        save_all_preferences(preferences)
        logger.info(f"Undismissed alert: {alert_id}")
    
    return {
        "ok": True,
        "message": f"Alert '{alert_id}' restored"
    }


@router.post("/config/dismissed-alerts/clear")
async def clear_dismissed_alerts() -> Dict[str, Any]:
    """
    Clear all dismissed alerts.
    
    Returns:
        Success status
    """
    preferences = load_all_preferences()
    preferences["dismissed_alerts"] = []
    save_all_preferences(preferences)
    
    logger.info("Cleared all dismissed alerts")
    
    return {
        "ok": True,
        "message": "All dismissed alerts cleared"
    }
