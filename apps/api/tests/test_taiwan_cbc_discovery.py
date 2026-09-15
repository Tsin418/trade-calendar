from datetime import date
from unittest.mock import AsyncMock

import pytest

from trade_calendar.adapters.errors import StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.taiwan import TaiwanCbcMeetingAdapter
from trade_calendar.adapters.types import RawPayload


def announcement(year: int) -> str:
    return f"""
    <h1>Provisional Schedule of Monetary Policy Meetings for {year}</h1>
    <p>The Bank announces the provisional schedule of Monetary Policy Meetings for {year}:</p>
    <p>March 19</p><p>June 18</p><p>September 17</p><p>December 17</p>
    <p>A news conference will take place after each meeting.</p>
    """


def listing(page: int) -> str:
    return f"https://www.cbc.gov.tw/en/lp-448-2-{page}-20.html"


def mock_fetcher(pages: dict[str, str]) -> HttpFetcher:
    async def get(source_key: str, url: str, headers: object) -> RawPayload:
        return RawPayload(
            source_key=source_key, url=url, content=pages[url].encode(), content_type="text/html"
        )

    fetcher = HttpFetcher(user_agent="test-suite")
    fetcher.get = AsyncMock(side_effect=get)  # type: ignore[method-assign]
    return fetcher


async def test_discovers_annual_schedule_after_it_moves_to_page_six() -> None:
    detail = "https://www.cbc.gov.tw/en/current.html"
    pages = {
        listing(page): f'<a href="/en/lp-448-2-{page + 1}-20.html">next</a>'
        for page in range(1, 6)
    }
    pages[listing(6)] = (
        '<a href="current.html">Provisional Schedule of Monetary Policy Meetings for 2026</a>'
    )
    pages[detail] = announcement(2026)
    adapter = TaiwanCbcMeetingAdapter(mock_fetcher(pages), today=lambda: date(2026, 9, 15))
    events = adapter.parse(await adapter.fetch())
    assert len(events) == 4
    assert events[-1].local_date == date(2026, 12, 17)
    assert all(event.url == detail for event in events)


async def test_preserves_current_year_when_next_year_schedule_is_published() -> None:
    pages = {
        listing(1): '<a href="next.html">Schedule of Monetary Policy Meetings for 2027</a>'
        '<a href="/en/lp-448-2-2-20.html">next</a>',
        listing(2): '<a href="current.html">Schedule of Monetary Policy Meetings for 2026</a>',
        "https://www.cbc.gov.tw/en/current.html": announcement(2026),
        "https://www.cbc.gov.tw/en/next.html": announcement(2027),
    }
    adapter = TaiwanCbcMeetingAdapter(mock_fetcher(pages), today=lambda: date(2026, 12, 20))
    events = adapter.parse(await adapter.fetch())
    assert len(events) == 8
    assert {event.local_date.year for event in events if event.local_date} == {2026, 2027}
    assert events[0].url == "https://www.cbc.gov.tw/en/current.html"
    assert events[-1].url == "https://www.cbc.gov.tw/en/next.html"


async def test_discovery_rejects_old_schedule_and_stops_at_page_limit() -> None:
    pages = {
        listing(page): '<a href="old.html">Schedule of Monetary Policy Meetings for 2025</a>'
        f'<a href="/en/lp-448-2-{page + 1}-20.html">next</a>'
        for page in range(1, 4)
    }
    adapter = TaiwanCbcMeetingAdapter(mock_fetcher(pages), today=lambda: date(2026, 9, 15))
    adapter.max_listing_pages = 3
    with pytest.raises(StructureChangedError, match="2026 is missing"):
        await adapter.fetch()


async def test_discovery_stops_when_the_index_has_no_next_page() -> None:
    adapter = TaiwanCbcMeetingAdapter(
        mock_fetcher({listing(1): '<a href="https://other.example">next</a>'}),
        today=lambda: date(2026, 9, 15),
    )
    with pytest.raises(StructureChangedError, match="2026 is missing"):
        await adapter.fetch()
