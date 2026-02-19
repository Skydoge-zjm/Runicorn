"""Unit tests for runicorn.extensions.monitors."""
from __future__ import annotations

import math

from runicorn.extensions.monitors import AlertRule, AnomalyDetector, MetricMonitor


class TestMetricMonitor:
    """MetricMonitor detects NaN, Inf, threshold violations."""

    def test_nan_detection(self):
        m = MetricMonitor()
        alerts = m.check_metrics({"loss": float("nan")})
        assert any("NAN" in a for a in alerts)

    def test_inf_detection(self):
        m = MetricMonitor()
        alerts = m.check_metrics({"loss": float("inf")})
        assert any("INF" in a for a in alerts)

    def test_threshold_rule(self):
        m = MetricMonitor()
        m.add_rule(AlertRule(metric_name="lr", condition="gt", threshold=1.0))
        alerts = m.check_metrics({"lr": 0.5})
        assert not any("lr" in a for a in alerts)

        alerts = m.check_metrics({"lr": 1.5})
        assert any("lr" in a for a in alerts)

    def test_no_alert_normal_values(self):
        m = MetricMonitor()
        alerts = m.check_metrics({"loss": 0.42, "acc": 0.95})
        assert alerts == []

    def test_get_statistics(self):
        m = MetricMonitor()
        m.check_metrics({"loss": 1.0})
        m.check_metrics({"loss": 2.0})
        m.check_metrics({"loss": 3.0})
        stats = m.get_statistics("loss")
        assert stats["mean"] == 2.0
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0
        assert stats["count"] == 3


class TestAnomalyDetector:
    """AnomalyDetector detects sudden metric changes."""

    def test_nan_is_anomaly(self):
        d = AnomalyDetector()
        assert d.is_anomaly("loss", float("nan")) is True

    def test_value_within_baseline(self):
        d = AnomalyDetector(sensitivity=2.0)
        d.update_baseline("loss", [1.0, 1.1, 0.9, 1.0, 1.05])
        assert d.is_anomaly("loss", 1.0) is False

    def test_value_outside_baseline(self):
        d = AnomalyDetector(sensitivity=2.0)
        d.update_baseline("loss", [1.0, 1.1, 0.9, 1.0, 1.05])
        assert d.is_anomaly("loss", 10.0) is True

    def test_detect_trend_anomaly(self):
        d = AnomalyDetector()
        # Stable baseline then sudden jump
        stable = [1.0] * 10
        jumped = stable + [5.0] * 5
        assert d.detect_trend_anomaly(jumped, window=5) is True

    def test_no_trend_anomaly_stable(self):
        d = AnomalyDetector()
        stable = [1.0, 1.01, 0.99, 1.0, 1.01, 0.99, 1.0, 1.01, 0.99, 1.0]
        assert d.detect_trend_anomaly(stable, window=5) is False


class TestAlertRule:
    """AlertRule dataclass construction."""

    def test_defaults(self):
        r = AlertRule(metric_name="loss", condition="nan")
        assert r.consecutive_count == 1
        assert r.threshold is None
        assert r.callback is None
