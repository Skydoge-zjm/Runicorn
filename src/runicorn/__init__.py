from __future__ import annotations

from .sdk import Run, init, get_active_run
from .config.registry import get_config
from .enabled import enabled, is_enabled, reset_enabled, set_enabled
from .config.rnconfig import get_effective_rnconfig
from .assets import snapshot_workspace
from ._version import __version__

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
    from .extensions.monitors import MetricMonitor, AnomalyDetector, AlertRule
    __all__.extend(["MetricMonitor", "AnomalyDetector", "AlertRule"])
except ImportError:
    pass

try:
    from .extensions.experiment import ExperimentManager, ExperimentMetadata
    __all__.extend(["ExperimentManager", "ExperimentMetadata"])
except ImportError:
    pass

try:
    from .extensions.exporters import MetricsExporter
    __all__.append("MetricsExporter")
except ImportError:
    pass

try:
    from .extensions.environment import EnvironmentCapture, EnvironmentInfo
    __all__.extend(["EnvironmentCapture", "EnvironmentInfo"])
except ImportError:
    pass
