"""
Utility functions for Runicorn API Client
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def metrics_to_dataframe(metrics_data: Dict[str, Any]) -> "pd.DataFrame":
    """
    Convert metrics API response to pandas DataFrame.
    
    Args:
        metrics_data: Response from client.get_metrics()
        
    Returns:
        DataFrame with columns: step, metric1, metric2, ...
        
    Example:
        >>> import runicorn.api as api
        >>> client = api.connect()
        >>> metrics = client.get_metrics("run_id")
        >>> df = api.utils.metrics_to_dataframe(metrics)
        >>> print(df.head())
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for this function. Install: pip install pandas")
    
    # Extract metrics
    metrics_dict = metrics_data.get("metrics", {})
    
    # Build DataFrame
    df_data = {}
    for metric_name, points in metrics_dict.items():
        steps = [p["step"] for p in points]
        values = [p["value"] for p in points]
        
        if not df_data:
            df_data["step"] = steps
        df_data[metric_name] = values
    
    return pd.DataFrame(df_data)


def experiments_to_dataframe(experiments: List[Dict[str, Any]]) -> "pd.DataFrame":
    """
    Convert experiments list to pandas DataFrame.
    
    Args:
        experiments: Response from client.list_experiments()
        
    Returns:
        DataFrame with experiment info
        
    Example:
        >>> import runicorn.api as api
        >>> client = api.connect()
        >>> experiments = client.list_experiments()
        >>> df = api.utils.experiments_to_dataframe(experiments)
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for this function. Install: pip install pandas")
    
    if not experiments:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(experiments)
    
    # Convert timestamps
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], unit="s")
    if "updated_at" in df.columns:
        df["updated_at"] = pd.to_datetime(df["updated_at"], unit="s")
    
    return df


def export_metrics_to_csv(
    client,
    run_id: str,
    output_path: str,
    metric_names: Optional[List[str]] = None,
) -> str:
    """
    Export metrics to CSV file.
    
    Args:
        client: RunicornClient instance
        run_id: Run ID
        output_path: Output CSV file path
        metric_names: Specific metrics to export (None = all)
        
    Returns:
        Path to saved CSV file
        
    Example:
        >>> import runicorn.api as api
        >>> client = api.connect()
        >>> api.utils.export_metrics_to_csv(
        ...     client, "run_id", "metrics.csv"
        ... )
    """
    # Get metrics
    metrics = client.get_metrics(run_id, metric_names=metric_names)
    
    # Convert to DataFrame
    df = metrics_to_dataframe(metrics)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    
    return output_path


def compare_runs(
    client,
    run_ids: List[str],
    metric_name: str,
) -> "pd.DataFrame":
    """
    Compare a specific metric across multiple runs.
    
    Args:
        client: RunicornClient instance
        run_ids: List of run IDs to compare
        metric_name: Metric name to compare
        
    Returns:
        DataFrame with columns: step, run_id_1, run_id_2, ...
        
    Example:
        >>> import runicorn.api as api
        >>> client = api.connect()
        >>> df = api.utils.compare_runs(
        ...     client,
        ...     ["run1", "run2", "run3"],
        ...     "loss"
        ... )
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for this function. Install: pip install pandas")
    
    comparison_data = {}
    
    for run_id in run_ids:
        metrics = client.get_metrics(run_id, metric_names=[metric_name])
        metrics_dict = metrics.get("metrics", {})
        
        if metric_name in metrics_dict:
            points = metrics_dict[metric_name]
            steps = [p["step"] for p in points]
            values = [p["value"] for p in points]
            
            if not comparison_data:
                comparison_data["step"] = steps
            comparison_data[run_id] = values
    
    return pd.DataFrame(comparison_data)
