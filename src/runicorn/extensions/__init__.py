"""
Runicorn Extensions Module

Optional extended functionality for advanced use cases.
These modules are not required for basic Runicorn usage.
"""

# Optional imports - gracefully handle missing dependencies
__all__ = []

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
