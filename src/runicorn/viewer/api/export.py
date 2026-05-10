"""
Data Export API Routes

Handles experiment data export in various formats.
"""
from __future__ import annotations

import logging
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from ...storage.file_utils import find_run_dir_by_id, read_json
from ..services.db_reader import find_run_entry_fast

logger = logging.getLogger(__name__)
router = APIRouter()

# Try to import metrics exporter if available
try:
    from ...exporters import MetricsExporter
    HAS_EXPORTER = True
except ImportError:
    MetricsExporter = None
    HAS_EXPORTER = False
    logger.debug("MetricsExporter not available")


@router.get("/export/{run_id}/csv")
async def export_csv(run_id: str, request: Request) -> Response:
    """
    Export run metrics as CSV.
    
    Args:
        run_id: Run ID to export
        
    Returns:
        CSV file response
        
    Raises:
        HTTPException: If exporter is not available or run not found
    """
    if not HAS_EXPORTER:
        raise HTTPException(status_code=501, detail="Export functionality not available")
    
    entry = find_run_entry_fast(request, run_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    try:
        exporter = MetricsExporter(entry.dir)
        csv_content = exporter.to_csv()
        
        if csv_content:
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={run_id}_metrics.csv"}
            )
        else:
            raise HTTPException(status_code=404, detail="No metrics to export")
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{run_id}/report")
async def export_report(run_id: str, request: Request, format: str = "markdown") -> Response:
    """
    Generate experiment report.
    
    Args:
        run_id: Run ID to generate report for
        format: Report format (markdown or html)
        
    Returns:
        Report file response
        
    Raises:
        HTTPException: If exporter is not available or format is invalid
    """
    if not HAS_EXPORTER:
        raise HTTPException(status_code=501, detail="Export functionality not available")
    
    if format not in ["markdown", "html"]:
        raise HTTPException(status_code=400, detail="Format must be markdown or html")
    
    entry = find_run_entry_fast(request, run_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    try:
        exporter = MetricsExporter(entry.dir)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format}', delete=False) as f:
            temp_path = Path(f.name)
        
        if format == "markdown":
            success = exporter._generate_markdown_report(temp_path)
        else:
            success = exporter._generate_html_report(temp_path)
        
        if success and temp_path.exists():
            content = temp_path.read_text(encoding='utf-8')
            temp_path.unlink()  # Clean up temp file
            
            media_type = "text/markdown" if format == "markdown" else "text/html"
            return Response(
                content=content,
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={run_id}_report.{format}"}
            )
        else:
            raise HTTPException(status_code=500, detail="Report generation failed")
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RunsExportRequest(BaseModel):
    run_ids: List[str]


@router.post("/runs/export")
async def export_runs_zip(request: Request, body: RunsExportRequest) -> FileResponse:
    """
    Export selected runs as a zip archive.
    
    The zip layout mirrors the storage structure: runs/<path>/<run_id>/<files>
    so it can be directly imported via POST /import/archive.
    
    Only files directly inside each run directory are included (not CAS blobs).
    """
    storage_root = request.app.state.storage_root
    run_ids = body.run_ids
    
    if not run_ids:
        raise HTTPException(status_code=400, detail="run_ids must not be empty")
    
    # Resolve run directories
    entries = []
    for rid in run_ids:
        entry = find_run_dir_by_id(storage_root, rid)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {rid}")
        entries.append(entry)
    
    # Create temp zip
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="runicorn_export_", suffix=".zip")
    os.close(tmp_fd)
    tmp_zip = Path(tmp_path)
    
    def _cleanup() -> None:
        try:
            if tmp_zip.exists():
                tmp_zip.unlink()
        except Exception:
            pass
    
    try:
        with zipfile.ZipFile(str(tmp_zip), "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for entry in entries:
                run_dir = entry.dir
                run_id = run_dir.name
                # Build archive prefix: runs/<path>/<run_id>/
                path_prefix = entry.path or ""
                if path_prefix:
                    arc_prefix = f"runs/{path_prefix}/{run_id}"
                else:
                    arc_prefix = f"runs/{run_id}"
                
                for dirpath, _, filenames in os.walk(run_dir):
                    dp = Path(dirpath)
                    for fn in filenames:
                        fp = dp / fn
                        try:
                            rel = fp.relative_to(run_dir).as_posix()
                            zf.write(str(fp), f"{arc_prefix}/{rel}")
                        except Exception:
                            pass
    except Exception as e:
        _cleanup()
        raise HTTPException(status_code=500, detail=f"Failed to create zip: {e}")
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"runicorn_export_{len(entries)}runs_{ts}.zip"
    return FileResponse(
        path=str(tmp_zip),
        filename=filename,
        media_type="application/zip",
        background=BackgroundTask(_cleanup),
    )


@router.get("/environment/{run_id}")
async def get_environment(run_id: str, request: Request) -> Dict[str, Any]:
    """
    Get environment information for a run.
    
    Args:
        run_id: Run ID to get environment for
        
    Returns:
        Environment information if available
        
    Raises:
        HTTPException: If run is not found
    """
    entry = find_run_entry_fast(request, run_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    env_path = entry.dir / "environment.json"
    if not env_path.exists():
        return {"available": False}
    
    try:
        env_data = read_json(env_path)
        return {"available": True, "environment": env_data}
    except Exception as e:
        logger.error(f"Failed to load environment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
