from __future__ import annotations

from .sdk import Run, init

__all__ = [
    "Run",
    "init",
]

# Optional artifacts import
try:
    from .artifacts import Artifact, ArtifactType
    __all__.extend(["Artifact", "ArtifactType"])
except ImportError:
    pass

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
