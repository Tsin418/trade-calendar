from datetime import date
from pathlib import Path

import pytest

from trade_calendar.adapters.errors import StructureChangedError
from trade_calendar.adapters.fed import FedFomcAdapter, parse_meeting_range
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import RawPayload
from trade_calendar.models.domain import DatePrecision, Importance

FIXTURE = Path(__file__).parent / "fixtures" / "fed" / "fomc-calendar.html"


def adapter() -> FedFomcAdapter:
    return FedFomcAdapter(HttpFetcher(user_agent="test-suite"))


def payload(content: bytes | None = None) -> RawPayload:
    return RawPayload(
        source_key="fed_fomc_calendar",
        url=FedFomcAdapter.url,
        content=content if content is not None else FIXTURE.read_bytes(),
        content_type="text/html",
    )


def test_fomc_fixture_parses_without_inventing_decision_time() -> None:
    instance = adapter()
    parsed = instance.parse(payload())
    normalized = [instance.normalize(event) for event in parsed]
    assert len(normalized) == 3
    assert normalized[1].source_event_id == "fomc-2026-02"
    assert normalized[1].local_date == date(2026, 9, 16)
    assert normalized[1].date_range_start == date(2026, 9, 15)
    assert normalized[1].date_range_end == date(2026, 9, 16)
    assert normalized[1].starts_at is None
    assert normalized[1].date_precision == DatePrecision.DATE
    assert normalized[1].importance == Importance.CRITICAL
    assert normalized[1].original_time_text is not None
    assert "decision time not listed" in normalized[1].original_time_text


def test_cross_month_range_uses_second_month_for_decision_date() -> None:
    start, end = parse_meeting_range(2027, "Jan/Feb", "31-1")
    assert start == date(2027, 1, 31)
    assert end == date(2027, 2, 1)


def test_fomc_structure_change_is_visible() -> None:
    with pytest.raises(StructureChangedError):
        adapter().parse(payload(b"<html><body>calendar unavailable</body></html>"))
