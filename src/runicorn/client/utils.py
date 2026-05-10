"""
Utility functions for Runicorn API Client
"""
from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def metrics_to_dataframe(metrics_data: Dict[str, Any]) -> "pd.DataFrame":
    """
    Convert metrics API response to pandas DataFrame.
    
    The server returns ``{columns: [...], rows: [{col: val, ...}, ...]}``.
    
    Args:
        metrics_data: Response from client.get_metrics()
        
    Returns:
        DataFrame with columns from the response
        
    Example:
        >>> import runicorn.client as client_mod
        >>> client = client_mod.connect()
        >>> metrics = client.get_metrics("run_id")
        >>> df = client_mod.utils.metrics_to_dataframe(metrics)
        >>> print(df.head())
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for this function. Install: pip install pandas")
    
    rows = metrics_data.get("rows", [])
    if not rows:
        columns = metrics_data.get("columns", [])
        return pd.DataFrame(columns=columns)
    
    return pd.DataFrame(rows)


def runs_to_dataframe(runs: List[Dict[str, Any]]) -> "pd.DataFrame":
    """
    Convert runs list to pandas DataFrame.
    
    Args:
        runs: Response from client.list_runs()
        
    Returns:
        DataFrame with run info
        
    Example:
        >>> import runicorn.client as client_mod
        >>> client = client_mod.connect()
        >>> runs = client.list_runs()
        >>> df = client_mod.utils.runs_to_dataframe(runs)
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for this function. Install: pip install pandas")
    
    if not runs:
        return pd.DataFrame()
    
    df = pd.DataFrame(runs)
    
    if "created_time" in df.columns:
        df["created_time"] = pd.to_datetime(df["created_time"], unit="s")
    
    return df


# Backward compatibility
experiments_to_dataframe = runs_to_dataframe


def export_metrics_to_csv(
    client,
    run_id: str,
    output_path: str,
) -> str:
    """
    Export metrics to CSV file.
    
    Args:
        client: RunicornClient instance
        run_id: Run ID
        output_path: Output CSV file path
        
    Returns:
        Path to saved CSV file
        
    Example:
        >>> import runicorn.client as client_mod
        >>> client = client_mod.connect()
        >>> client_mod.utils.export_metrics_to_csv(
        ...     client, "run_id", "metrics.csv"
        ... )
    """
    metrics = client.get_metrics(run_id)
    df = metrics_to_dataframe(metrics)
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
        DataFrame with columns: global_step, run_id_1, run_id_2, ...
        
    Example:
        >>> import runicorn.client as client_mod
        >>> client = client_mod.connect()
        >>> df = client_mod.utils.compare_runs(
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
        metrics = client.get_metrics(run_id)
        rows = metrics.get("rows", [])
        
        steps = [r.get("global_step", i) for i, r in enumerate(rows)]
        values = [r.get(metric_name) for r in rows]
        
        if not comparison_data:
            comparison_data["global_step"] = steps
        comparison_data[run_id] = values
    
    return pd.DataFrame(comparison_data)
