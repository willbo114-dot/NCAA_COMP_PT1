"""Output utilities for the College Basketball Scraper."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Iterable, Sequence

try:  # pragma: no cover - optional dependency
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover
    pd = None  # type: ignore


def _extract_records(data: Any) -> tuple[list[str], list[dict[str, Any]]]:
    if pd is not None and isinstance(data, pd.DataFrame):
        columns = list(data.columns)
        records = data.to_dict(orient="records")
        return columns, records
    if isinstance(data, list) and data and isinstance(data[0], dict):
        columns = list(data[0].keys())
        return columns, data
    if hasattr(data, "columns") and hasattr(data, "rows"):
        columns = list(getattr(data, "columns"))
        rows = list(getattr(data, "rows"))
        return columns, rows
    return [], []


def write_outputs(
    df_logs: Any,
    df_summary: Any,
    out_csv: Path,
    out_xlsx: Path,
) -> None:
    """Write CSV and Excel outputs and attempt to open the workbook on Windows."""

    columns_logs, records_logs = _extract_records(df_logs)
    columns_summary, records_summary = _extract_records(df_summary)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns_logs)
        writer.writeheader()
        for row in records_logs:
            writer.writerow({col: row.get(col) for col in columns_logs})

    try:  # pragma: no cover - requires optional dependency
        from openpyxl import Workbook  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("openpyxl is required to write Excel files") from exc

    wb = Workbook()
    ws_raw = wb.active
    ws_raw.title = "stats_raw"
    ws_raw.append(columns_logs)
    for row in records_logs:
        ws_raw.append([row.get(col) for col in columns_logs])

    ws_summary = wb.create_sheet("summary_players")
    ws_summary.append(columns_summary)
    for row in records_summary:
        ws_summary.append([row.get(col) for col in columns_summary])

    wb.save(out_xlsx)

    if os.name == "nt":  # pragma: no cover - Windows specific
        try:
            os.startfile(out_xlsx)  # type: ignore[attr-defined]
        except OSError:
            pass


__all__ = ["write_outputs"]
