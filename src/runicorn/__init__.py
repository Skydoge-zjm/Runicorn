from __future__ import annotations

from .sdk import Run, init, get_active_run
from .registry import get_config
from .enabled import enabled, is_enabled, reset_enabled, set_enabled
from .rnconfig import get_effective_rnconfig
from .assets import snapshot_workspace

# Version information
try:
    from pathlib import Path
    # Try multiple locations for VERSION.txt
    # 1. For installed package: same level as package root
    _version_file = Path(__file__).parent.parent.parent / "VERSION.txt"
    if not _version_file.exists():
        # 2. For editable install or package data
        _version_file = Path(__file__).parent / "VERSION.txt"
    
    if _version_file.exists():
        __version__ = _version_file.read_text().strip()
    else:
        __version__ = "0.6.0"
except Exception:
    __version__ = "0.6.0"

__all__ = [
    "Run",
    "init",
    "get_active_run",
    "get_config",
    "snapshot_workspace",
    "enabled",
    "is_enabled",
    "set_enabled",
    "reset_enabled",
    "get_effective_rnconfig",
    "__version__",
]

# Optional imports for extended functionality
try:
    from .monitors import MetricMonitor, AnomalyDetector, AlertRule
    __all__.extend(["MetricMonitor", "AnomalyDetector", "AlertRule"])
except ImportError:
    pass

try:
    from .experiment import ExperimentManager, ExperimentMetadata
    __all__.extend(["ExperimentManager", "ExperimentMetadata"])
except ImportError:
    pass

try:
    from .exporters import MetricsExporter
    __all__.append("MetricsExporter")
except ImportError:
    pass

try:
    from .environment import EnvironmentCapture, EnvironmentInfo
    __all__.extend(["EnvironmentCapture", "EnvironmentInfo"])
except ImportError:
    pass
