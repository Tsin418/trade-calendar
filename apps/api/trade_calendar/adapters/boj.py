import hashlib
import re
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from selectolax.parser import HTMLParser

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance

TOKYO = ZoneInfo("Asia/Tokyo")
MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "aug": 8,
    "sept": 9,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
MONTH_PATTERN = re.compile(r"\b(Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Sep|Oct|Nov|Dec)\.", re.I)
TIME_PATTERN = re.compile(r"(\d{1,2}):(\d{2})")


class BojMeetingAdapter(SourceAdapter):
    source_key = "boj_mpm"
    version = "1.0.0"
    url = "https://www.boj.or.jp/en/mopo/mpmsche_minu/"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self) -> RawPayload:
        return await self.fetcher.get(self.source_key, self.url, {"Accept": "text/html"})

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        tree = HTMLParser(payload.content)
        years = [
            int(node.text(strip=True))
            for node in tree.css("h2")
            if re.fullmatch(r"20\d{2}", node.text(strip=True))
        ]
        tables = tree.css("table")
        events: list[SourceEvent] = []
        for year, table in zip(years, tables, strict=False):
            for row in table.css("tr"):
                cells = row.css("th,td")
                if not cells:
                    continue
                value = cells[0].text(separator=" ", strip=True)
                month_match = MONTH_PATTERN.search(value)
                days = [int(item) for item in re.findall(r"(\d{1,2})\s*\(", value)]
                if month_match is None or not days:
                    continue
                month = MONTHS[month_match.group(1).casefold()]
                decision_date = date(year, month, days[-1])
                events.append(SourceEvent(
                    source_event_id=f"boj-mpm-{decision_date.isoformat()}",
                    title="Bank of Japan Monetary Policy Meeting",
                    local_date=decision_date,
                    original_timezone="Asia/Tokyo",
                    original_time_text=value,
                    url=payload.url,
                    raw={"meeting_dates": value, "year": year},
                ))
        if not events:
            raise StructureChangedError("BOJ meeting page contained no recognizable dates")
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.local_date is None:
            raise StructureChangedError("BOJ meeting is missing a decision date")
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh="日本央行利率决议",
            title_original=event.title,
            institution="Bank of Japan",
            country_code="JP",
            category="monetary_policy",
            event_type="central_bank_decision",
            status=(
                EventStatus.COMPLETED
                if event.local_date < datetime.now(TOKYO).date()
                else EventStatus.TBA
            ),
            importance=Importance.CRITICAL,
            date_precision=DatePrecision.DATE,
            local_date=event.local_date,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            market_tags=["JP", "GLOBAL"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


class BojReleaseScheduleAdapter(SourceAdapter):
    source_key = "boj_release_schedule"
    version = "1.0.0"
    url = "https://www.boj.or.jp/en/about/calendar/index.htm"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self) -> RawPayload:
        return await self.fetcher.get(self.source_key, self.url, {"Accept": "text/html"})

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        tree = HTMLParser(payload.content)
        table = tree.css_first("table")
        if table is None:
            raise StructureChangedError("BOJ release schedule table is missing")
        rows = [[cell.text(separator=" ", strip=True) for cell in row.css("th,td")]
                for row in table.css("tr")]
        events = parse_boj_release_rows(rows, datetime.now(TOKYO).date(), payload.url)
        if not events:
            raise StructureChangedError("BOJ release schedule contained no recognizable rows")
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        event_type, importance = classify_boj_release(event.title)
        if event.starts_at is not None:
            precision = (
                DatePrecision.HOUR
                if (event.original_time_text or "").casefold().startswith("around")
                else DatePrecision.MINUTE
            )
            status = (
                EventStatus.COMPLETED
                if event.starts_at < datetime.now(UTC)
                else EventStatus.CONFIRMED
            )
        else:
            precision = DatePrecision.DATE
            status = (
                EventStatus.COMPLETED
                if event.local_date and event.local_date < datetime.now(TOKYO).date()
                else EventStatus.TBA
            )
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh=translate_boj_title(event.title),
            title_original=event.title,
            institution="Bank of Japan",
            country_code="JP",
            category=(
                "monetary_policy" if event_type.startswith("central_bank") else "macro_release"
            ),
            event_type=event_type,
            status=status,
            importance=importance,
            date_precision=precision,
            starts_at=event.starts_at,
            local_date=event.local_date,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            market_tags=["JP", "GLOBAL"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


def parse_boj_release_rows(
    rows: list[list[str]], today: date, source_url: str
) -> list[SourceEvent]:
    events: list[SourceEvent] = []
    current_date: date | None = None
    for cells in rows:
        if len(cells) < 3 or cells[0].casefold() == "date":
            continue
        date_text, time_text, title = (value.strip() for value in cells[:3])
        if date_text:
            month_match = MONTH_PATTERN.search(date_text)
            day_match = re.search(r"\b(\d{1,2})\b", date_text)
            if month_match and day_match:
                month = MONTHS[month_match.group(1).casefold()]
                day = int(day_match.group(1))
                year = nearest_year(today, month, day)
                current_date = date(year, month, day)
            elif current_date and date_text.isdigit():
                current_date = date(current_date.year, current_date.month, int(date_text))
        if current_date is None or not title:
            continue
        time_match = TIME_PATTERN.search(time_text)
        starts_at = None
        if time_match:
            local = datetime(
                current_date.year,
                current_date.month,
                current_date.day,
                int(time_match.group(1)),
                int(time_match.group(2)),
                tzinfo=TOKYO,
            )
            starts_at = local.astimezone(UTC)
        digest = hashlib.sha256(title.encode()).hexdigest()[:14]
        events.append(SourceEvent(
            source_event_id=f"boj-release-{current_date:%Y%m%d}-{digest}",
            title=title,
            starts_at=starts_at,
            local_date=None if starts_at else current_date,
            original_timezone="Asia/Tokyo",
            original_time_text=f"{current_date.isoformat()} {time_text}".strip(),
            url=source_url,
            raw={"date": current_date.isoformat(), "time": time_text, "title": title},
        ))
    return events


def nearest_year(today: date, month: int, day: int) -> int:
    candidates = [date(year, month, day) for year in range(today.year - 1, today.year + 2)]
    return min(candidates, key=lambda value: abs((value - today).days)).year


def classify_boj_release(title: str) -> tuple[str, Importance]:
    lowered = title.casefold()
    if "statement on monetary policy" in lowered:
        return "central_bank_decision", Importance.CRITICAL
    if "speech" in lowered:
        return "central_bank_speech", Importance.MEDIUM
    if "cpi" in lowered or "price index" in lowered:
        return "inflation", Importance.HIGH
    if "exports" in lowered or "imports" in lowered:
        return "trade", Importance.MEDIUM
    return "activity", Importance.LOW


def translate_boj_title(title: str) -> str:
    lowered = title.casefold()
    if "statement on monetary policy" in lowered:
        return "日本央行货币政策声明"
    if "core cpi" in lowered:
        return "日本央行核心 CPI 指标"
    if "price index" in lowered:
        return f"日本央行物价数据：{title}"
    if "speech" in lowered:
        return f"日本央行委员讲话：{title}"
    return f"日本央行：{title}"
