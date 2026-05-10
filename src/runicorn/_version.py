from __future__ import annotations

from pathlib import Path

_FALLBACK_VERSION = "0.0.0+unknown"


def _version_candidates() -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    return (
        here.with_name("VERSION.txt"),
        here.parents[2] / "VERSION.txt",
    )


def get_version(default: str = _FALLBACK_VERSION) -> str:
    for candidate in _version_candidates():
        try:
            if candidate.exists():
                value = candidate.read_text(encoding="utf-8").strip()
                if value:
                    return value
        except OSError:
            continue
    return default


__version__ = get_version()

