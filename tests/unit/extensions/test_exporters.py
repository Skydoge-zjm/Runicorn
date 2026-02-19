"""Unit tests for runicorn.extensions.exporters."""
from __future__ import annotations

import json
from pathlib import Path

from runicorn.extensions.exporters import MetricsExporter


def _setup_run_dir(tmp_path: Path) -> Path:
    """Create a minimal run directory with events and metadata."""
    run = tmp_path / "run"
    run.mkdir()

    events = [
        {"type": "metrics", "data": {"global_step": 1, "loss": 0.9, "acc": 0.1}},
        {"type": "metrics", "data": {"global_step": 2, "loss": 0.5, "acc": 0.5}},
        {"type": "metrics", "data": {"global_step": 3, "loss": 0.2, "acc": 0.9}},
    ]
    (run / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    (run / "meta.json").write_text(
        json.dumps({"project": "p", "name": "e", "id": "r1", "created_at": 1000}),
        encoding="utf-8",
    )
    return run


class TestMetricsExporterCsv:
    """MetricsExporter.to_csv reads events.jsonl and returns CSV."""

    def test_returns_csv_string(self, tmp_path: Path):
        run = _setup_run_dir(tmp_path)
        exporter = MetricsExporter(run)
        csv_str = exporter.to_csv()
        assert csv_str is not None
        lines = csv_str.strip().splitlines()
        # Header + 3 data rows + comment lines
        data_lines = [l for l in lines if not l.startswith("#")]
        assert len(data_lines) == 4  # header + 3 rows
        assert "loss" in data_lines[0]

    def test_writes_to_file(self, tmp_path: Path):
        run = _setup_run_dir(tmp_path)
        out = tmp_path / "metrics.csv"
        exporter = MetricsExporter(run)
        result = exporter.to_csv(output_path=out)
        assert result is None  # writes to file, returns None
        assert out.exists()
        assert "loss" in out.read_text(encoding="utf-8")

    def test_empty_events_returns_none(self, tmp_path: Path):
        run = tmp_path / "empty_run"
        run.mkdir()
        exporter = MetricsExporter(run)
        assert exporter.to_csv() is None


class TestMetricsExporterMarkdown:
    """MetricsExporter.generate_report with markdown format."""

    def test_generates_markdown(self, tmp_path: Path):
        run = _setup_run_dir(tmp_path)
        out = tmp_path / "report.md"
        exporter = MetricsExporter(run)
        ok = exporter.generate_report(out, format="markdown")
        assert ok is True
        content = out.read_text(encoding="utf-8")
        assert "# Experiment Report" in content
        assert "loss" in content
