"""
Monitoring and alerting module for Runicorn.
Provides anomaly detection for training metrics.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    """Define alert rules for metric monitoring."""
    metric_name: str
    condition: str  # 'gt', 'lt', 'eq', 'ne', 'nan', 'inf'
    threshold: Optional[float] = None
    consecutive_count: int = 1  # How many consecutive times before alerting
    callback: Optional[Callable[[str, Any], None]] = None


class MetricMonitor:
    """Monitor metrics for anomalies and trigger alerts."""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize metric monitor.
        
        Args:
            window_size: Size of rolling window for statistics
        """
        self.window_size = window_size
        self.metrics_history: Dict[str, deque] = {}
        self.alert_rules: List[AlertRule] = []
        self.consecutive_violations: Dict[str, int] = {}
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """Setup default alert rules for common issues."""
        # Loss explosion detection
        self.add_rule(AlertRule(
            metric_name="loss",
            condition="nan",
            consecutive_count=1,
            callback=self._log_alert
        ))
        self.add_rule(AlertRule(
            metric_name="loss",
            condition="inf",
            consecutive_count=1,
            callback=self._log_alert
        ))
        # Add rules for common metric patterns
        for metric in ["train_loss", "val_loss", "test_loss"]:
            self.add_rule(AlertRule(
                metric_name=metric,
                condition="nan",
                consecutive_count=1,
                callback=self._log_alert
            ))
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self.alert_rules.append(rule)
        self.consecutive_violations[f"{rule.metric_name}_{rule.condition}"] = 0
    
    def check_metrics(self, metrics: Dict[str, Any]) -> List[str]:
        """
        Check metrics against alert rules.
        
        Args:
            metrics: Dictionary of metric values
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        
        # Update history
        for name, value in metrics.items():
            if name not in self.metrics_history:
                self.metrics_history[name] = deque(maxlen=self.window_size)
            
            if isinstance(value, (int, float)):
                self.metrics_history[name].append(value)
        
        # Check rules
        for rule in self.alert_rules:
            if rule.metric_name in metrics:
                value = metrics[rule.metric_name]
                if self._check_condition(value, rule.condition, rule.threshold):
                    rule_key = f"{rule.metric_name}_{rule.condition}"
                    self.consecutive_violations[rule_key] += 1
                    
                    if self.consecutive_violations[rule_key] >= rule.consecutive_count:
                        alert_msg = self._format_alert(rule, value)
                        alerts.append(alert_msg)
                        
                        if rule.callback:
                            try:
                                rule.callback(alert_msg, value)
                            except Exception as e:
                                logger.error(f"Alert callback failed: {e}")
                        
                        # Reset counter after alert
                        self.consecutive_violations[rule_key] = 0
                else:
                    # Reset counter if condition not met
                    rule_key = f"{rule.metric_name}_{rule.condition}"
                    self.consecutive_violations[rule_key] = 0
        
        return alerts
    
    def _check_condition(self, value: Any, condition: str, threshold: Optional[float]) -> bool:
        """Check if value meets condition."""
        try:
            if not isinstance(value, (int, float)):
                return False
            
            if condition == "nan":
                return math.isnan(value)
            elif condition == "inf":
                return math.isinf(value)
            elif condition == "gt" and threshold is not None:
                return value > threshold
            elif condition == "lt" and threshold is not None:
                return value < threshold
            elif condition == "eq" and threshold is not None:
                return abs(value - threshold) < 1e-9
            elif condition == "ne" and threshold is not None:
                return abs(value - threshold) >= 1e-9
        except Exception as e:
            logger.debug(f"Condition check failed: {e}")
        
        return False
    
    def _format_alert(self, rule: AlertRule, value: Any) -> str:
        """Format alert message."""
        if rule.condition in ["nan", "inf"]:
            return f"⚠️ Alert: {rule.metric_name} is {rule.condition.upper()}"
        else:
            return f"⚠️ Alert: {rule.metric_name}={value} {rule.condition} {rule.threshold}"
    
    def _log_alert(self, message: str, value: Any) -> None:
        """Default alert callback - log to console."""
        logger.warning(message)
    
    def get_statistics(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        if metric_name not in self.metrics_history or len(self.metrics_history[metric_name]) == 0:
            return {}
        
        values = list(self.metrics_history[metric_name])
        
        # Filter out NaN and Inf values for statistics
        valid_values = [v for v in values if not math.isnan(v) and not math.isinf(v)]
        
        if not valid_values:
            return {"has_nan": any(math.isnan(v) for v in values),
                    "has_inf": any(math.isinf(v) for v in values)}
        
        return {
            "mean": sum(valid_values) / len(valid_values),
            "min": min(valid_values),
            "max": max(valid_values),
            "last": values[-1],
            "count": len(values),
            "valid_count": len(valid_values)
        }


class AnomalyDetector:
    """Detect anomalies in metric trends."""
    
    def __init__(self, sensitivity: float = 2.0):
        """
        Initialize anomaly detector.
        
        Args:
            sensitivity: Standard deviation multiplier for anomaly threshold
        """
        self.sensitivity = sensitivity
        self.baselines: Dict[str, Dict[str, float]] = {}
    
    def update_baseline(self, metric_name: str, values: List[float]) -> None:
        """Update baseline statistics for a metric."""
        valid_values = [v for v in values if not math.isnan(v) and not math.isinf(v)]
        
        if len(valid_values) < 2:
            return
        
        mean = sum(valid_values) / len(valid_values)
        variance = sum((v - mean) ** 2 for v in valid_values) / len(valid_values)
        std_dev = math.sqrt(variance)
        
        self.baselines[metric_name] = {
            "mean": mean,
            "std": std_dev,
            "upper_bound": mean + self.sensitivity * std_dev,
            "lower_bound": mean - self.sensitivity * std_dev
        }
    
    def is_anomaly(self, metric_name: str, value: float) -> bool:
        """Check if a value is anomalous."""
        if math.isnan(value) or math.isinf(value):
            return True
        
        if metric_name not in self.baselines:
            return False
        
        baseline = self.baselines[metric_name]
        return value > baseline["upper_bound"] or value < baseline["lower_bound"]
    
    def detect_trend_anomaly(self, values: List[float], window: int = 5) -> bool:
        """
        Detect if recent trend is anomalous.
        
        Args:
            values: List of metric values
            window: Size of recent window to check
            
        Returns:
            True if anomalous trend detected
        """
        if len(values) < window * 2:
            return False
        
        recent = values[-window:]
        previous = values[-window*2:-window]
        
        # Check for sudden jumps
        recent_mean = sum(recent) / len(recent)
        previous_mean = sum(previous) / len(previous)
        
        if previous_mean != 0:
            change_ratio = abs(recent_mean - previous_mean) / abs(previous_mean)
            if change_ratio > 0.5:  # 50% sudden change
                return True
        
        # Check for increasing variance (instability)
        recent_var = sum((v - recent_mean) ** 2 for v in recent) / len(recent)
        previous_var = sum((v - previous_mean) ** 2 for v in previous) / len(previous)
        
        if previous_var != 0:
            var_ratio = recent_var / previous_var
            if var_ratio > 3:  # Variance tripled
                return True
        
        return False


# Integration with SDK
def create_monitor_callback(monitor: MetricMonitor) -> Callable:
    """Create a callback for SDK integration."""
    def callback(metrics: Dict[str, Any]) -> None:
        alerts = monitor.check_metrics(metrics)
        for alert in alerts:
            logger.warning(alert)
    return callback
