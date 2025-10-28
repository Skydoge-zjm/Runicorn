from __future__ import annotations

from .sdk import Run, init

# Version information
try:
    from pathlib import Path
    _version_file = Path(__file__).parent.parent.parent / "VERSION.txt"
    if _version_file.exists():
        __version__ = _version_file.read_text().strip()
    else:
        __version__ = "0.5.0.dev0"
except Exception:
    __version__ = "0.5.0.dev0"

__all__ = [
    "Run",
    "init",
    "__version__",
]

# Optional artifacts import
try:
    from .artifacts import Artifact, ArtifactType
    __all__.extend(["Artifact", "ArtifactType"])
except ImportError:
    pass

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
