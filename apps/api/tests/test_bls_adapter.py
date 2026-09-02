from pathlib import Path

import pytest

from trade_calendar.adapters.bls import (
    BlsCalendarAdapter,
    raw_payload_from_fixture,
)
from trade_calendar.adapters.errors import StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.models.domain import DatePrecision, Importance

FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "calendar.ics"


def adapter() -> BlsCalendarAdapter:
    return BlsCalendarAdapter(HttpFetcher(user_agent="test-suite"))


def test_bls_ics_fixture_parses_and_normalizes() -> None:
    instance = adapter()
    events = instance.parse(raw_payload_from_fixture(FIXTURE.read_bytes()))
    normalized = [instance.normalize(event) for event in events]

    assert len(normalized) == 3
    assert normalized[0].source_event_id == "employment-2026-09@bls.gov"
    assert normalized[0].title_zh == "美国就业报告"
    assert normalized[0].importance == Importance.HIGH
    assert normalized[0].date_precision == DatePrecision.MINUTE
    assert normalized[0].starts_at.isoformat() == "2026-09-04T12:30:00+00:00"
    assert normalized[0].original_timezone == "America/New_York"
    assert instance.health_check(normalized).healthy is True


def test_bls_adapter_rejects_structure_change() -> None:
    empty = raw_payload_from_fixture(
        b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
    )
    with pytest.raises(StructureChangedError):
        adapter().parse(empty)


def test_bls_date_only_event_remains_date_only() -> None:
    content = b"""BEGIN:VCALENDAR\r
VERSION:2.0\r
BEGIN:VEVENT\r
UID:date-only@bls.gov\r
DTSTART;VALUE=DATE:20260908\r
SUMMARY:Annual Reference Release\r
END:VEVENT\r
END:VCALENDAR\r
"""
    instance = adapter()
    normalized = instance.normalize(instance.parse(raw_payload_from_fixture(content))[0])
    assert normalized.date_precision == DatePrecision.DATE
    assert normalized.local_date.isoformat() == "2026-09-08"
    assert normalized.starts_at is None

