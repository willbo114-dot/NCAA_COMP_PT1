"""Date utilities for the College Basketball Scraper."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, Iterator


ISO_DATE_FMT = "%Y-%m-%d"


class DateParseError(ValueError):
    """Raised when a user-supplied date string cannot be parsed."""


def parse_date(raw: str | date | datetime) -> date:
    """Parse a string into a :class:`~datetime.date`.

    Parameters
    ----------
    raw:
        A date-like object or ISO-8601 string (``YYYY-MM-DD``).

    Returns
    -------
    datetime.date
        The parsed date.

    Raises
    ------
    DateParseError
        If the input cannot be interpreted as a valid date.
    """

    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if not isinstance(raw, str):
        raise DateParseError("Expected a string in YYYY-MM-DD format.")
    try:
        return datetime.strptime(raw, ISO_DATE_FMT).date()
    except ValueError as exc:  # pragma: no cover - error branch
        raise DateParseError(
            f"Could not parse '{raw}'. Please supply YYYY-MM-DD."
        ) from exc


def daterange(start: date, end: date) -> Iterable[date]:
    """Yield dates inclusively between ``start`` and ``end``.

    Parameters
    ----------
    start, end:
        Inclusive boundaries of the range. Order does not matter; the
        implementation normalizes the bounds.
    """

    if not isinstance(start, date) or not isinstance(end, date):
        raise TypeError("daterange expects date objects.")

    if end < start:
        start, end = end, start

    delta = (end - start).days
    for offset in range(delta + 1):
        yield start + timedelta(days=offset)


__all__ = ["DateParseError", "parse_date", "daterange", "ISO_DATE_FMT"]
