import calendar
import re
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from selectolax.parser import HTMLParser

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance

YEAR_PATTERN = re.compile(r"(20\d{2})\s+FOMC Meetings", re.IGNORECASE)
DAY_PATTERN = re.compile(r"(\d{1,2})(?:\s*-\s*(\d{1,2}))?")
MONTHS = {name.casefold(): index for index, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.casefold(): index for index, name in enumerate(calendar.month_abbr) if name})


class FedFomcAdapter(SourceAdapter):
    source_key = "fed_fomc_calendar"
    version = "1.0.0"
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self) -> RawPayload:
        return await self.fetcher.get(self.source_key, self.url, {"Accept": "text/html"})

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        tree = HTMLParser(payload.content)
        events: list[SourceEvent] = []
        for panel in tree.css("div.panel.panel-default"):
            heading = panel.css_first(".panel-heading")
            match = YEAR_PATTERN.search(heading.text(strip=True) if heading else "")
            if not match:
                continue
            year = int(match.group(1))
            for ordinal, row in enumerate(panel.css(".fomc-meeting"), start=1):
                month_node = row.css_first(".fomc-meeting__month")
                day_node = row.css_first(".fomc-meeting__date")
                if month_node is None or day_node is None:
                    continue
                month_text = month_node.text(strip=True)
                day_text = day_node.text(strip=True)
                start_date, end_date = parse_meeting_range(year, month_text, day_text)
                event_id = f"fomc-{year}-{ordinal:02d}"
                events.append(SourceEvent(
                    source_event_id=event_id,
                    title="Federal Open Market Committee Meeting",
                    local_date=end_date,
                    date_range_start=start_date,
                    date_range_end=end_date,
                    original_timezone="America/New_York",
                    original_time_text=f"{month_text} {day_text}, {year}; decision time not listed",
                    url=payload.url,
                    raw={
                        "meeting_start_date": start_date.isoformat(),
                        "meeting_end_date": end_date.isoformat(),
                        "month_text": month_text,
                        "day_text": day_text,
                    },
                ))
        if not events:
            raise StructureChangedError("FOMC page did not contain recognizable meeting rows")
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.local_date is None:
            raise StructureChangedError("FOMC meeting is missing a decision date")
        today_et = datetime.now(UTC).astimezone(ZoneInfo("America/New_York")).date()
        status = EventStatus.COMPLETED if event.local_date < today_et else EventStatus.TBA
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh="FOMC 利率决议",
            title_original=event.title,
            institution="Federal Reserve",
            country_code="US",
            category="monetary_policy",
            event_type="central_bank_decision",
            status=status,
            importance=Importance.CRITICAL,
            date_precision=DatePrecision.DATE,
            local_date=event.local_date,
            date_range_start=event.date_range_start,
            date_range_end=event.date_range_end,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            market_tags=["US", "GLOBAL"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


def parse_meeting_range(year: int, month_text: str, day_text: str) -> tuple[date, date]:
    month_parts = [part.strip().casefold() for part in month_text.split("/")]
    month_numbers = [MONTHS.get(part) for part in month_parts]
    start_month = month_numbers[0]
    end_month = month_numbers[-1]
    if start_month is None or end_month is None:
        raise StructureChangedError(f"unknown FOMC month: {month_text}")
    day_match = DAY_PATTERN.search(day_text.replace("*", ""))
    if not day_match:
        raise StructureChangedError(f"unknown FOMC date: {day_text}")
    start_day = int(day_match.group(1))
    end_day = int(day_match.group(2) or start_day)
    end_year = year + 1 if end_month < start_month else year
    return date(year, start_month, start_day), date(end_year, end_month, end_day)
