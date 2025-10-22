"""Console display helpers."""

from __future__ import annotations

from typing import Any, Iterable, Sequence

try:  # pragma: no cover - optional dependency
    from tabulate import tabulate as _tabulate
except ImportError:  # pragma: no cover
    def _tabulate(rows: Sequence[Sequence[Any]], headers: Sequence[str], tablefmt: str, showindex: bool) -> str:
        if not rows:
            return "| " + " | ".join(headers) + " |\n" + "| " + " | ".join(["--"] * len(headers)) + " |"
        header_line = "| " + " | ".join(headers) + " |"
        sep = "|" + "---|" * len(headers)
        body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
        return "\n".join([header_line, sep, *body])

try:  # pragma: no cover - optional dependency
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover
    pd = None  # type: ignore


def _coerce_records(data: Any, max_rows: int) -> tuple[list[str], list[list[Any]]]:
    if pd is not None and isinstance(data, pd.DataFrame):
        subset = data.head(max_rows)
        headers = list(subset.columns)
        records = subset.to_dict(orient="records")
        return headers, [[record.get(h) for h in headers] for record in records]
    if isinstance(data, list):
        if not data:
            return [], []
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            rows = [[row.get(h) for h in headers] for row in data[:max_rows]]
            return headers, rows
        if isinstance(data[0], (list, tuple)):
            headers = [f"col_{i}" for i in range(len(data[0]))]
            return headers, [list(row) for row in data[:max_rows]]
    if hasattr(data, "rows") and hasattr(data, "columns"):
        headers = list(getattr(data, "columns"))
        rows = [
            [row.get(h) for h in headers]
            for row in getattr(data, "rows")[:max_rows]
        ]
        return headers, rows
    return [], []


def preview_table(data: Any, *, max_rows: int = 10) -> str:
    headers, rows = _coerce_records(data, max_rows)
    if not rows:
        return "(no rows)"
    return _tabulate(rows, headers=headers, tablefmt="github", showindex=False)


__all__ = ["preview_table"]
