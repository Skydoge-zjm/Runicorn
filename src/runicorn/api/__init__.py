"""
Backward compatibility shim — use ``runicorn.client`` instead.
"""
from __future__ import annotations

# Re-export everything from the new location
from ..client import *  # noqa: F401,F403
from ..client import connect, RunicornClient, __all__  # noqa: F401
