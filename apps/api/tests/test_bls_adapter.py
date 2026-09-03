import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from trade_calendar.adapters.bls import (
    LONGBRIDGE_CALENDAR_URL,
    BlsCalendarAdapter,
    raw_payload_from_fixture,
)
from trade_calendar.adapters.errors import StructureChangedError
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance

FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "calendar.json"


def adapter() -> BlsCalendarAdapter:
    return BlsCalendarAdapter(
        today=lambda: date(2026, 9, 3),
        now=lambda: datetime(2026, 9, 3, tzinfo=UTC),
    )


def test_bls_calendar_fixture_groups_release_components_and_normalizes() -> None:
    instance = adapter()
    events = instance.parse(raw_payload_from_fixture(FIXTURE.read_bytes()))
    normalized = [instance.normalize(event) for event in events]

    assert len(normalized) == 6
    by_title = {item.title_zh: item for item in normalized}
    employment = by_title["美国就业报告"]
    assert employment.source_event_id == "longbridge:employment-situation:august-2026"
    assert employment.importance == Importance.HIGH
    assert employment.date_precision == DatePrecision.MINUTE
    assert employment.starts_at.isoformat() == "2026-09-04T12:30:00+00:00"
    assert employment.original_timezone == "America/New_York"
    assert employment.reference_period == "August 2026"
    assert employment.status == EventStatus.EXPECTED
    assert employment.raw["provider_ids"] == ["nonfarm-payrolls", "unemployment-rate"]
    assert employment.source_url == LONGBRIDGE_CALENDAR_URL
    assert "美国非农生产力与成本（初值）" in by_title
    assert "美国非农生产力与成本（修正值）" in by_title
    assert by_title["美国非农生产力与成本（初值）"].reference_period == "Q2 2026"
    assert "美国生产者价格指数" in by_title
    assert "美国消费者价格指数" in by_title
    assert "美国职位空缺与劳动力流动调查" in by_title
    assert instance.health_check(normalized).healthy is True


def test_bls_adapter_rejects_structure_change() -> None:
    empty = raw_payload_from_fixture(b'{"provider":"Longbridge","list":[]}')
    with pytest.raises(StructureChangedError):
        adapter().parse(empty)


def test_bls_calendar_filters_non_bls_rows() -> None:
    content = """{
      "list": [{"date":"2026-09-10","infos": [
        {"id":"benchmark","market":"US",
         "content":"美国, 非农就业年度修正初值","datetime":"1787925600","star":2,
         "ext":{},"data_kv":[]},
        {"id":"claims","market":"US",
         "content":"美国, 初请失业金人数","datetime":"1789043400","star":3,
         "ext":{},"data_kv":[]},
        {"id":"gdp","market":"US",
         "content":"美国, GDP增长率","datetime":"1789043400","star":3,
         "ext":{},"data_kv":[]},
        {"id":"ppi","market":"US",
         "content":"美国, 最终需求PPI","datetime":"1789043400","star":3,
         "ext":{"period":"2026-08","unit":"百分比"},"data_kv":[]}
      ]}]
    }""".encode()
    instance = adapter()
    normalized = [
        instance.normalize(item)
        for item in instance.parse(raw_payload_from_fixture(content))
    ]
    assert [item.title_zh for item in normalized] == [
        "美国非农就业年度基准修订（初值）",
        "美国生产者价格指数",
    ]


async def test_bls_fetch_chunks_long_ranges_for_cli_calendar() -> None:
    calls: list[tuple[date, date]] = []

    async def fake_runner(start: date, end: date) -> dict[str, object]:
        calls.append((start, end))
        return {"date": start.isoformat(), "list": [], "next_date": "", "result": {}}

    instance = BlsCalendarAdapter(
        today=lambda: date(2026, 9, 3),
        now=lambda: datetime(2026, 9, 3, tzinfo=UTC),
        command_runner=fake_runner,
    )
    payload = await instance.fetch()
    document = json.loads(payload.content)

    assert len(calls) == 17
    assert calls[0] == (date(2026, 8, 3), date(2026, 8, 15))
    assert calls[-1] == (date(2027, 2, 27), date(2027, 3, 2))
    assert len(document["queries"]) == 17
    assert document["provider"] == "Longbridge"
