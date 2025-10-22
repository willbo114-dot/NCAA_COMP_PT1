"""Filesystem helpers."""

from __future__ import annotations

from pathlib import Path


DATA_ROOT = Path("data")
RAW_DIR = DATA_ROOT / "raw"
PROCESSED_DIR = DATA_ROOT / "processed"


def ensure_dirs() -> None:
    """Ensure the output directory structure exists."""

    for path in (RAW_DIR, PROCESSED_DIR):
        path.mkdir(parents=True, exist_ok=True)


def raw_csv_path(label: str) -> Path:
    """Return a CSV path for a given label in the raw data folder."""

    safe = label.replace(" ", "_")
    return RAW_DIR / f"logs_{safe}.csv"


def xlsx_path(label: str) -> Path:
    """Return an Excel path for a given label in the processed data folder."""

    safe = label.replace(" ", "_")
    return PROCESSED_DIR / f"report_{safe}.xlsx"


__all__ = ["ensure_dirs", "raw_csv_path", "xlsx_path", "DATA_ROOT", "RAW_DIR", "PROCESSED_DIR"]
