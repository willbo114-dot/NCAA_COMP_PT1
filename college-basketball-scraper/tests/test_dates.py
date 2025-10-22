from datetime import date

import pytest

from cbs.utils.dates import DateParseError, daterange, parse_date


def test_parse_date_success():
    assert parse_date("2024-03-15").isoformat() == "2024-03-15"


def test_parse_date_failure():
    with pytest.raises(DateParseError):
        parse_date("15-03-2024")


def test_daterange_inclusive():
    days = list(daterange(date(2024, 3, 1), date(2024, 3, 3)))
    assert [d.day for d in days] == [1, 2, 3]


def test_daterange_reverse_order():
    days = list(daterange(date(2024, 3, 3), date(2024, 3, 1)))
    assert [d.day for d in days] == [1, 2, 3]
