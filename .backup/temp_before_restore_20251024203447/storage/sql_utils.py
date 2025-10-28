"""
SQL Utilities for Safe Query Construction

Provides utilities for safe SQL query construction and validation.
"""
from __future__ import annotations

import re
from typing import List, Set

# Whitelist of allowed column names for experiments table
ALLOWED_EXPERIMENT_COLUMNS = {
    'name', 'project', 'status', 'start_time', 'end_time',
    'duration', 'tags', 'config', 'metrics_summary', 'best_metric',
    'best_metric_value', 'best_metric_step', 'environment', 'notes',
    'updated_at', 'is_deleted', 'deleted_at', 'deleted_reason'
}

# Pattern for valid column names (alphanumeric + underscore only)
VALID_COLUMN_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')


def validate_column_name(column: str, allowed_columns: Set[str] = None) -> bool:
    """
    Validate a column name for SQL safety.
    
    Args:
        column: Column name to validate
        allowed_columns: Optional set of allowed column names
        
    Returns:
        True if column name is safe, False otherwise
    """
    # Check basic pattern
    if not VALID_COLUMN_PATTERN.match(column):
        return False
    
    # Check against whitelist if provided
    if allowed_columns and column not in allowed_columns:
        return False
    
    # Check for SQL keywords
    sql_keywords = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
        'ALTER', 'GRANT', 'REVOKE', 'UNION', 'FROM', 'WHERE',
        'JOIN', 'ORDER', 'GROUP', 'HAVING', 'AS', 'OR', 'AND'
    }
    
    if column.upper() in sql_keywords:
        return False
    
    return True


def safe_column_list(columns: List[str], allowed_columns: Set[str] = None) -> List[str]:
    """
    Filter and validate a list of column names.
    
    Args:
        columns: List of column names
        allowed_columns: Optional set of allowed column names
        
    Returns:
        List of safe column names
        
    Raises:
        ValueError: If any column name is invalid
    """
    safe_columns = []
    
    for column in columns:
        if not validate_column_name(column, allowed_columns):
            raise ValueError(f"Invalid column name: {column}")
        safe_columns.append(column)
    
    return safe_columns
