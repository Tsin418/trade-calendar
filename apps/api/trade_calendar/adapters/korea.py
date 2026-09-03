import json
import re
from collections.abc import Callable
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from selectolax.parser import HTMLParser

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import ParseError, StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance

SEOUL = ZoneInfo("Asia/Seoul")
KOREA_ENGLISH_SCHEDULE_URL = "https://mods.go.kr/schdl.es?mid=a20301000000"
KOREA_RELEASE_PLAN_URL = (
    "https://mods.go.kr/newsPln.es?mid=a10305000000&oa_mm=ALL"
)
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


class KoreaStatisticsCalendarAdapter(SourceAdapter):
    source_key = "korea_statistics_calendar"
    version = "2.0.0"
    url = KOREA_ENGLISH_SCHEDULE_URL

    def __init__(
        self,
        fetcher: HttpFetcher,
        today: Callable[[], date] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.fetcher = fetcher
        self.today = today or (lambda: datetime.now(SEOUL).date())
        self.now = now or (lambda: datetime.now(UTC))

    async def fetch(self) -> RawPayload:
        english = await self.fetcher.get(
            self.source_key,
            self.url,
            {"Accept": "text/html"},
        )
        korean = await self.fetcher.get(
            self.source_key,
            KOREA_RELEASE_PLAN_URL,
            {"Accept": "text/html"},
        )
        content = json.dumps({
            "english_url": english.url,
            "english_html": english.content.decode("utf-8"),
            "korean_url": korean.url,
            "korean_html": korean.content.decode("utf-8"),
        }, ensure_ascii=False).encode()
        return RawPayload(
            source_key=self.source_key,
            url=english.url,
            content=content,
            content_type="application/json",
        )

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        try:
            document = json.loads(payload.content)
            english_html = str(document["english_html"])
            korean_html = str(document["korean_html"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ParseError("invalid aggregated Korea release schedule") from exc
        times, korean_titles = parse_korean_release_times(korean_html, self.today().year)
        tree = HTMLParser(english_html)
        heading = next(
            (
                node.text(separator=" ", strip=True)
                for node in tree.css("h3")
                if "Schedule" in node.text()
            ),
            "",
        )
        year_match = re.search(r"(20\d{2})", heading)
        year = int(year_match.group(1)) if year_match else self.today().year
        events: dict[str, SourceEvent] = {}
        for row in tree.css("tr.center, table tbody tr"):
            cells = row.css("td")
            if len(cells) < 3:
                continue
            title = cells[1].text(separator=" ", strip=True)
            event_type, importance = classify_english_release(title)
            release_date = parse_english_release_date(cells[2].text(strip=True), year)
            if not title or release_date is None or event_type is None:
                continue
            local_time = times.get((release_date, event_type))
            korean_title = korean_titles.get((release_date, event_type))
            starts_at = local_time.astimezone(UTC) if local_time else None
            source_id = f"mods-en:{event_type}:{release_date.isoformat()}"
            events[source_id] = SourceEvent(
                source_event_id=source_id,
                title=title,
                starts_at=starts_at,
                local_date=None if starts_at else release_date,
                original_timezone="Asia/Seoul",
                original_time_text=(
                    f"{local_time:%Y-%m-%d %H:%M} Asia/Seoul"
                    if local_time
                    else release_date.isoformat()
                ),
                reference_period=extract_english_reference_period(title),
                status_text=(
                    "completed" if release_date < self.today() else "confirmed"
                ),
                url=str(document.get("english_url") or payload.url),
                raw={
                    "title_en": title,
                    "title_ko": korean_title,
                    "release_date": release_date.isoformat(),
                    "release_time": f"{local_time:%H:%M}" if local_time else None,
                    "division": cells[3].text(separator=" ", strip=True)
                    if len(cells) > 3
                    else "",
                    "korean_url": document.get("korean_url"),
                    "importance": importance.value,
                },
            )
        if not events:
            raise StructureChangedError(
                "Korea English schedule contained no recognizable release rows"
            )
        return list(events.values())

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        event_type, importance = classify_english_release(event.title)
        if event_type is None:
            raise StructureChangedError("Korea statistics release type is unknown")
        event_date = (
            event.starts_at.astimezone(SEOUL).date()
            if event.starts_at
            else event.local_date
        )
        if event_date is None:
            raise StructureChangedError("Korea statistics release is missing a date")
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh=translate_english_korean_title(event.title),
            title_original=event.title,
            institution="Ministry of Data and Statistics, Republic of Korea",
            country_code="KR",
            category="macro_release",
            event_type=event_type,
            status=(
                EventStatus.COMPLETED
                if event_date < self.today()
                else EventStatus.CONFIRMED
            ),
            importance=importance,
            date_precision=DatePrecision.MINUTE if event.starts_at else DatePrecision.DATE,
            starts_at=event.starts_at,
            local_date=event.local_date,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            reference_period=event.reference_period,
            market_tags=["KR"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


def parse_korean_release_times(
    html: str,
    year: int,
) -> tuple[
    dict[tuple[date, str], datetime],
    dict[tuple[date, str], str],
]:
    tree = HTMLParser(html)
    times: dict[tuple[date, str], datetime] = {}
    titles: dict[tuple[date, str], str] = {}
    for row in tree.css("tr.tr-notice, table tbody tr"):
        cells = row.css("td")
        if len(cells) < 3:
            continue
        date_match = re.search(
            r"(\d{1,2})\.(\d{1,2})\.",
            cells[0].text(separator=" ", strip=True),
        )
        time_match = re.search(r"(\d{1,2}):(\d{2})", cells[1].text(strip=True))
        title = cells[2].text(separator=" ", strip=True)
        event_type, _ = classify_korean_release(title)
        if date_match is None or time_match is None or event_type is None:
            continue
        try:
            local = datetime(
                year,
                int(date_match.group(1)),
                int(date_match.group(2)),
                int(time_match.group(1)),
                int(time_match.group(2)),
                tzinfo=SEOUL,
            )
        except ValueError:
            continue
        key = (local.date(), event_type)
        times[key] = local
        titles[key] = title
    return times, titles


def parse_english_release_date(value: str, year: int) -> date | None:
    match = re.search(r"([A-Za-z]{3})\.?\s+(\d{1,2})", value)
    if match is None:
        return None
    month = MONTHS.get(match.group(1).casefold())
    if month is None:
        return None
    try:
        return date(year, month, int(match.group(2)))
    except ValueError:
        return None


def classify_english_release(title: str) -> tuple[str | None, Importance]:
    lowered = title.casefold()
    if "consumer price" in lowered:
        return "inflation", Importance.HIGH
    if "economically active population" in lowered or "employment" in lowered:
        return "employment", Importance.HIGH
    if "industrial statistics" in lowered or "industrial production" in lowered:
        return "activity", Importance.HIGH
    return None, Importance.LOW


def classify_korean_release(title: str) -> tuple[str | None, Importance]:
    if "소비자물가동향" in title:
        return "inflation", Importance.HIGH
    if "고용동향" in title and "지역별" not in title:
        return "employment", Importance.HIGH
    if "산업활동동향" in title:
        return "activity", Importance.HIGH
    return None, Importance.LOW


def translate_english_korean_title(title: str) -> str:
    event_type, _ = classify_english_release(title)
    if event_type is None:
        return title
    return {
        "inflation": "韩国消费者物价指数",
        "employment": "韩国就业数据",
        "activity": "韩国工业活动数据",
    }[event_type]


def extract_english_reference_period(title: str) -> str | None:
    match = re.search(
        r"(?:in|,)?\s*(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(20\d{2})",
        title,
        re.I,
    )
    if match is None:
        return None
    month = MONTHS[match.group(1)[:3].casefold()]
    return f"{match.group(2)}-{month:02d}"
