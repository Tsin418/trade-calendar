import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from selectolax.parser import HTMLParser

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance

SEOUL = ZoneInfo("Asia/Seoul")
MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
DATE_PATTERN = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.\s*(\d{1,2})\b",
    re.I,
)


class BokMeetingAdapter(SourceAdapter):
    source_key = "bok_mpb"
    version = "1.0.0"
    url = "https://www.bok.or.kr/eng/main/contents.do?menuNo=400020"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self) -> RawPayload:
        return await self.fetcher.get(self.source_key, self.url, {"Accept": "text/html"})

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        tree = HTMLParser(payload.content)
        year_node = next(
            (node for node in tree.css("h3") if re.fullmatch(r"20\d{2}", node.text(strip=True))),
            None,
        )
        table = tree.css_first("table")
        if year_node is None or table is None:
            raise StructureChangedError("BOK meeting year or table is missing")
        year = int(year_node.text(strip=True))
        events: list[SourceEvent] = []
        for cell in table.css("td"):
            value = cell.text(separator=" ", strip=True)
            match = DATE_PATTERN.search(value)
            if match is None:
                continue
            meeting_date = date(year, MONTHS[match.group(1).casefold()], int(match.group(2)))
            events.append(SourceEvent(
                source_event_id=f"bok-mpb-{meeting_date.isoformat()}",
                title="Bank of Korea Monetary Policy Board Meeting",
                local_date=meeting_date,
                original_timezone="Asia/Seoul",
                original_time_text=value,
                url=payload.url,
                raw={"meeting_date": value, "year": year},
            ))
        if not events:
            raise StructureChangedError("BOK meeting page contained no recognizable dates")
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.local_date is None:
            raise StructureChangedError("BOK meeting is missing a decision date")
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh="韩国央行利率决议",
            title_original=event.title,
            institution="Bank of Korea",
            country_code="KR",
            category="monetary_policy",
            event_type="central_bank_decision",
            status=(
                EventStatus.COMPLETED
                if event.local_date < datetime.now(SEOUL).date()
                else EventStatus.TBA
            ),
            importance=Importance.CRITICAL,
            date_precision=DatePrecision.DATE,
            local_date=event.local_date,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            market_tags=["KR", "GLOBAL"],
            source_url=event.url or self.url,
            raw=event.raw,
        )
