"""
Analytics API v2 - Advanced Data Analysis

Provides high-performance analytics endpoints for experiment data analysis.
These endpoints leverage SQLite's analytical capabilities for real-time insights.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, Query, HTTPException

from ...services.modern_storage import get_storage_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/analytics/overview")
async def get_analytics_overview(request: Request) -> Dict[str, Any]:
    """
    Get comprehensive analytics overview.
    
    Returns:
        System-wide analytics and statistics
    """
    storage_service = get_storage_service(request.app.state.storage_root)
    
    # Get storage statistics
    storage_stats = await storage_service.get_storage_statistics()
    
    # Additional overview metrics would be computed here
    # For now, return the storage stats
    return {
        "overview": {
            "total_experiments": storage_stats["statistics"]["total_experiments"],
            "active_experiments": storage_stats["statistics"]["active_experiments"], 
            "running_experiments": 0,  # Would be computed from status
            "success_rate": 0.0,  # Would be computed
            "avg_experiment_duration": 0.0,  # Would be computed
            "storage_size_mb": storage_stats["statistics"]["db_size_mb"],
            "query_performance": {
                "avg_query_time_ms": storage_stats["performance"]["avg_query_time_ms"],
                "cache_hit_rate": storage_stats["performance"]["cache_hit_rate"]
            }
        },
        "storage_info": storage_stats,
        "generated_at": time.time()
    }


@router.get("/analytics/projects")  
async def get_project_analytics(
    request: Request,
    days: int = Query(30, description="Analysis period in days")
) -> Dict[str, Any]:
    """
    Get project-level analytics.
    
    Args:
        days: Analysis period in days
        
    Returns:
        Project analytics including success rates and performance trends
    """
    storage_service = get_storage_service(request.app.state.storage_root)
    
    # This would implement SQL analytics queries
    # For now, return a placeholder structure
    return {
        "projects": [],
        "analysis_period_days": days,
        "generated_at": time.time()
    }


@router.get("/analytics/performance-trends")
async def get_performance_trends(
    request: Request,
    metric_name: str = Query(..., description="Metric to analyze"),
    project: Optional[str] = Query(None, description="Filter by project"),
    days: int = Query(30, description="Analysis period in days")
) -> Dict[str, Any]:
    """
    Get performance trend analysis for a specific metric.
    
    Args:
        metric_name: Name of metric to analyze
        project: Optional project filter
        days: Analysis period in days
        
    Returns:
        Performance trend data and statistics
    """
    storage_service = get_storage_service(request.app.state.storage_root)
    
    # This would implement trend analysis queries
    # For now, return a placeholder structure
    return {
        "metric_name": metric_name,
        "project": project,
        "trend_data": [],
        "statistics": {
            "total_experiments": 0,
            "mean_value": 0.0,
            "std_dev": 0.0,
            "min_value": 0.0,
            "max_value": 0.0
        },
        "analysis_period_days": days,
        "generated_at": time.time()
    }


@router.get("/analytics/health")
async def get_system_health(request: Request) -> Dict[str, Any]:
    """
    Get system health metrics including storage performance.
    
    Returns:
        System health indicators and performance metrics
    """
    storage_service = get_storage_service(request.app.state.storage_root)
    
    try:
        # Test query performance
        test_start = time.time()
        await storage_service.list_experiments(limit=1)
        test_query_time = (time.time() - test_start) * 1000
        
        # Get storage stats
        storage_stats = await storage_service.get_storage_statistics()
        
        # Calculate health score
        health_score = 100.0
        health_issues = []
        
        # Check query performance
        if test_query_time > 100:  # > 100ms is concerning
            health_score -= 20
            health_issues.append(f"Slow queries detected: {test_query_time:.1f}ms")
        
        # Check storage size
        db_size_mb = storage_stats["statistics"]["db_size_mb"]
        if db_size_mb > 1000:  # > 1GB database
            health_score -= 10
            health_issues.append(f"Large database size: {db_size_mb:.1f}MB")
        
        health_status = "excellent" if health_score >= 95 else \
                       "good" if health_score >= 80 else \
                       "fair" if health_score >= 60 else "poor"
        
        return {
            "health_status": health_status,
            "health_score": health_score,
            "issues": health_issues,
            "performance": {
                "test_query_time_ms": round(test_query_time, 2),
                "avg_query_time_ms": storage_stats["performance"]["avg_query_time_ms"],
                "cache_hit_rate": storage_stats["performance"]["cache_hit_rate"]
            },
            "storage": {
                "backend_type": storage_stats["backend_type"],
                "storage_type": storage_stats["storage_type"],
                "db_size_mb": db_size_mb,
                "total_experiments": storage_stats["statistics"]["total_experiments"]
            },
            "checked_at": time.time()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")
