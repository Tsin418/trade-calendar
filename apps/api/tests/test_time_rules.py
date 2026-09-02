from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from trade_calendar.schemas.events import EventCreate


def base_payload() -> dict[str, object]:
    return {
        "title_zh": "测试事件",
        "institution": "Official Institution",
        "country_code": "US",
        "category": "macro_release",
        "event_type": "inflation",
        "importance": "high",
    }


def test_dst_boundary_converts_using_iana_timezone() -> None:
    new_york = ZoneInfo("America/New_York")
    before_fallback = datetime(2026, 11, 1, 1, 30, tzinfo=new_york, fold=0)
    after_fallback = datetime(2026, 11, 1, 1, 30, tzinfo=new_york, fold=1)
    assert before_fallback.astimezone(UTC) == datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
    assert after_fallback.astimezone(UTC) == datetime(2026, 11, 1, 6, 30, tzinfo=UTC)


def test_time_window_requires_end() -> None:
    with pytest.raises(ValidationError):
        EventCreate.model_validate({
            **base_payload(),
            "date_precision": "window",
            "starts_at": "2026-09-02T09:00:00+08:00",
        })


def test_unknown_precision_does_not_require_fake_time() -> None:
    event = EventCreate.model_validate({
        **base_payload(),
        "date_precision": "unknown",
        "status": "expected",
        "local_date": date(2026, 12, 1),
    })
    assert event.starts_at is None

