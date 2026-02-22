"""Tests for runicorn.viewer.utils.incremental_cache — IncrementalMetricsCache."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from runicorn.viewer.utils.incremental_cache import IncrementalMetricsCache


def _write_events(path: Path, events: list[dict]) -> None:
    """Write JSONL events file."""
    lines = [json.dumps(e) for e in events]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_metric_event(step: int, **metrics) -> dict:
    """Create a metrics event dict for events.jsonl."""
    return {"ts": time.time(), "type": "metrics", "data": {"global_step": step, **metrics}}


@pytest.fixture
def cache():
    c = IncrementalMetricsCache(max_size=5, stale_threshold=60)
    yield c
    c.clear()


class TestFullRead:
    def test_full_read_new_file(self, cache: IncrementalMetricsCache, tmp_path: Path):
        """First read of a file performs a full parse."""
        events_path = tmp_path / "events.jsonl"
        _write_events(events_path, [
            _make_metric_event(1, loss=0.5, acc=0.8),
            _make_metric_event(2, loss=0.3, acc=0.9),
        ])

        cols, rows = cache.get_or_update(events_path)
        assert "global_step" in cols
        assert "loss" in cols
        assert "acc" in cols
        assert len(rows) == 2
        assert rows[0]["global_step"] == 1
        assert rows[1]["loss"] == 0.3

    def test_cache_hit_same_size(self, cache: IncrementalMetricsCache, tmp_path: Path):
        """Same file size → cache hit, no re-read."""
        events_path = tmp_path / "events.jsonl"
        _write_events(events_path, [_make_metric_event(1, loss=0.5)])

        cache.get_or_update(events_path)
        stats_before = cache.stats()
        cache.get_or_update(events_path)  # should be cache hit
        stats_after = cache.stats()

        assert stats_after["hits"] == stats_before["hits"] + 1

    def test_nonexistent_file_returns_empty(self, cache: IncrementalMetricsCache, tmp_path: Path):
        """Non-existent file returns empty lists."""
        cols, rows = cache.get_or_update(tmp_path / "nope.jsonl")
        assert cols == []
        assert rows == []


class TestIncrementalRead:
    def test_incremental_append(self, cache: IncrementalMetricsCache, tmp_path: Path):
        """Appending to file triggers incremental read, not full re-parse."""
        events_path = tmp_path / "events.jsonl"
        _write_events(events_path, [_make_metric_event(1, loss=0.5)])

        cols1, rows1 = cache.get_or_update(events_path)
        assert len(rows1) == 1

        # Append a new event
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(_make_metric_event(2, loss=0.3)) + "\n")

        cols2, rows2 = cache.get_or_update(events_path)
        assert len(rows2) == 2
        assert rows2[1]["loss"] == 0.3

        stats = cache.stats()
        assert stats["incremental_updates"] >= 1

    def test_truncation_triggers_full_reread(self, cache: IncrementalMetricsCache, tmp_path: Path):
        """If file shrinks (truncation), cache is invalidated and full re-read happens."""
        events_path = tmp_path / "events.jsonl"
        _write_events(events_path, [
            _make_metric_event(1, loss=0.5),
            _make_metric_event(2, loss=0.3),
        ])

        cache.get_or_update(events_path)

        # Truncate: rewrite with fewer events
        _write_events(events_path, [_make_metric_event(10, loss=0.1)])

        cols, rows = cache.get_or_update(events_path)
        assert len(rows) == 1
        assert rows[0]["global_step"] == 10


class TestStats:
    def test_stats_fields(self, cache: IncrementalMetricsCache, tmp_path: Path):
        """stats() returns all expected fields."""
        events_path = tmp_path / "events.jsonl"
        _write_events(events_path, [_make_metric_event(1, x=1)])

        cache.get_or_update(events_path)  # miss
        cache.get_or_update(events_path)  # hit

        s = cache.stats()
        assert set(s.keys()) >= {"size", "max_size", "hits", "misses",
                                  "incremental_updates", "hit_rate", "incremental_rate"}
        assert s["hits"] == 1
        assert s["misses"] == 1
        assert s["size"] == 1


class TestEviction:
    def test_lru_eviction(self, cache: IncrementalMetricsCache, tmp_path: Path):
        """Exceeding max_size triggers LRU eviction."""
        # max_size=5 in fixture
        for i in range(6):
            p = tmp_path / f"events_{i}.jsonl"
            _write_events(p, [_make_metric_event(1, val=i)])
            cache.get_or_update(p)

        assert cache.stats()["size"] <= 5
