"""Tests for runicorn.sdk — log_image and log_text."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runicorn.sdk import Run


def _make_run(storage_root: Path, monkeypatch: pytest.MonkeyPatch, **kw) -> Run:
    monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))
    defaults = dict(path="test/media", storage=str(storage_root),
                    capture_console=False, run_id="media_001")
    defaults.update(kw)
    return Run(**defaults)


class TestLogImage:
    def test_log_image_from_bytes(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Raw bytes are written directly to media/."""
        run = _make_run(storage_root, monkeypatch, run_id="img_bytes_001")
        try:
            raw = b"\x89PNG\r\n\x1a\nfakedata"
            rel = run.log_image("sample", raw, step=1)
            assert rel.startswith("media/")
            saved = run.run_dir / rel
            assert saved.exists()
            assert saved.read_bytes() == raw

            # Event recorded
            events = run._events_path.read_text(encoding="utf-8").strip().splitlines()
            evt = json.loads(events[-1])
            assert evt["type"] == "image"
            assert evt["data"]["key"] == "sample"
        finally:
            run.finish()

    def test_log_image_from_file_path(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """A path-like argument is copied into media/."""
        src = tmp_path / "input.png"
        src.write_bytes(b"fakepng")

        run = _make_run(storage_root, monkeypatch, run_id="img_path_001")
        try:
            rel = run.log_image("from_file", str(src))
            saved = run.run_dir / rel
            assert saved.exists()
            assert saved.read_bytes() == b"fakepng"
        finally:
            run.finish()

    def test_log_image_from_pil(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """PIL Image object — calls image.save()."""
        run = _make_run(storage_root, monkeypatch, run_id="img_pil_001")
        try:
            mock_img = MagicMock()
            mock_img.save = MagicMock()
            # Needs `hasattr(image, 'save')` to be True, and HAS_PIL to be True
            with patch("runicorn.sdk.HAS_PIL", True):
                run.log_image("pil_img", mock_img, format="png")
            mock_img.save.assert_called_once()
            call_args = mock_img.save.call_args
            assert str(call_args[0][0]).endswith(".png")
        finally:
            run.finish()

    def test_log_image_from_numpy(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Numpy array — converted via PIL.Image.fromarray then saved."""
        run = _make_run(storage_root, monkeypatch, run_id="img_np_001")
        try:
            # Use spec to prevent auto-generated .save so it doesn't match PIL branch
            mock_arr = MagicMock(spec=["shape", "dtype", "__array__"])
            mock_arr.shape = (100, 100, 3)
            mock_pil_img = MagicMock()

            with patch("runicorn.sdk.HAS_PIL", True), \
                 patch("runicorn.sdk.HAS_NUMPY", True), \
                 patch("runicorn.sdk.Image") as MockImage:
                MockImage.fromarray.return_value = mock_pil_img
                run.log_image("np_img", mock_arr)

            MockImage.fromarray.assert_called_once_with(mock_arr)
            mock_pil_img.save.assert_called_once()
        finally:
            run.finish()

    def test_log_image_missing_file_raises(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """Non-existent path raises FileNotFoundError."""
        run = _make_run(storage_root, monkeypatch, run_id="img_missing_001")
        try:
            with pytest.raises(FileNotFoundError):
                run.log_image("gone", "/nonexistent/image.png")
        finally:
            run.finish()


class TestLogText:
    def test_log_text_writes_file(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """log_text appends to logs.txt."""
        run = _make_run(storage_root, monkeypatch, run_id="text_001")
        try:
            run.log_text("hello world")
            run.log_text("second line")
            content = run._logs_txt_path.read_text(encoding="utf-8")
            assert "hello world" in content
            assert "second line" in content
            # Each line has a timestamp prefix
            lines = content.strip().splitlines()
            assert len(lines) == 2
        finally:
            run.finish()
