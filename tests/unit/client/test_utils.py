"""Unit tests for runicorn.client.utils."""
from __future__ import annotations

import time

import pandas as pd
import pytest

from runicorn.client.utils import metrics_to_dataframe, runs_to_dataframe


class TestMetricsToDataframe:

    def test_basic_conversion(self) -> None:
        data = {
            "columns": ["global_step", "loss", "acc"],
            "rows": [
                {"global_step": 1, "loss": 0.5, "acc": 0.8},
                {"global_step": 2, "loss": 0.3, "acc": 0.9},
            ],
            "total": 2,
        }
        df = metrics_to_dataframe(data)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "loss" in df.columns
        assert df["loss"].iloc[0] == 0.5

    def test_empty_rows_preserves_columns(self) -> None:
        data = {"columns": ["global_step", "loss"], "rows": [], "total": 0}
        df = metrics_to_dataframe(data)
        assert list(df.columns) == ["global_step", "loss"]
        assert len(df) == 0

    def test_missing_rows_key(self) -> None:
        df = metrics_to_dataframe({"columns": ["a"]})
        assert len(df) == 0


class TestRunsToDataframe:

    def test_basic_conversion(self) -> None:
        now = time.time()
        runs = [
            {"id": "r1", "status": "finished", "path": "a/b", "created_time": now},
            {"id": "r2", "status": "running", "path": "a/c", "created_time": now + 1},
        ]
        df = runs_to_dataframe(runs)
        assert len(df) == 2
        assert df["id"].iloc[0] == "r1"
        # created_time should be converted to datetime
        assert pd.api.types.is_datetime64_any_dtype(df["created_time"])

    def test_empty_list(self) -> None:
        df = runs_to_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
