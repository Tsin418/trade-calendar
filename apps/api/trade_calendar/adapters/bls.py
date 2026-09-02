from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from icalendar import Calendar

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import ParseError, StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance


class BlsCalendarAdapter(SourceAdapter):
    source_key = "us_bls_calendar"
    version = "1.0.0"
    url = "https://www.bls.gov/schedule/news_release/bls.ics"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self) -> RawPayload:
        return await self.fetcher.get(self.source_key, self.url, {"Accept": "text/calendar"})

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        try:
            calendar = Calendar.from_ical(payload.content)
        except Exception as exc:
            raise ParseError("invalid ICS payload") from exc
        events: list[SourceEvent] = []
        for component in calendar.walk("VEVENT"):
            uid = str(component.get("UID", "")).strip()
            title = str(component.get("SUMMARY", "")).strip()
            if not uid or not title or component.get("DTSTART") is None:
                continue
            start = component.decoded("DTSTART")
            end = component.decoded("DTEND") if component.get("DTEND") else None
            source_event = SourceEvent(
                source_event_id=uid,
                title=title,
                description=str(component.get("DESCRIPTION", "")) or None,
                url=str(component.get("URL", payload.url)),
                raw={"uid": uid, "summary": title},
            )
            if isinstance(start, datetime):
                if start.tzinfo is None:
                    start = start.replace(tzinfo=ZoneInfo("America/New_York"))
                source_event.starts_at = start.astimezone(UTC)
                source_event.ends_at = (
                    end.astimezone(UTC) if isinstance(end, datetime) and end.tzinfo else None
                )
                source_event.original_timezone = "America/New_York"
                source_event.original_time_text = start.astimezone(
                    ZoneInfo("America/New_York")
                ).strftime("%Y-%m-%d %H:%M ET")
            elif isinstance(start, date):
                source_event.local_date = start
            events.append(source_event)
        if not events:
            raise StructureChangedError("ICS parsed successfully but contained no valid VEVENT")
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        event_type, importance = classify_bls_release(event.title)
        precision = DatePrecision.MINUTE if event.starts_at else DatePrecision.DATE
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh=translate_bls_title(event.title),
            title_original=event.title,
            institution="U.S. Bureau of Labor Statistics",
            country_code="US",
            category="macro_release",
            event_type=event_type,
            status=EventStatus.CONFIRMED,
            importance=importance,
            date_precision=precision,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            local_date=event.local_date,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            market_tags=["US", "GLOBAL"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


def classify_bls_release(title: str) -> tuple[str, Importance]:
    lowered = title.casefold()
    rules: list[tuple[tuple[str, ...], str, Importance]] = [
        (("employment situation",), "employment", Importance.HIGH),
        (("consumer price index",), "inflation", Importance.HIGH),
        (("producer price index",), "inflation", Importance.HIGH),
        (("productivity",), "activity", Importance.MEDIUM),
        (("job openings",), "employment", Importance.MEDIUM),
    ]
    for keywords, event_type, importance in rules:
        if any(keyword in lowered for keyword in keywords):
            return event_type, importance
    return "activity", Importance.MEDIUM


def translate_bls_title(title: str) -> str:
    translations: dict[str, str] = {
        "The Employment Situation": "美国就业报告",
        "Consumer Price Index": "美国消费者价格指数",
        "Producer Price Index": "美国生产者价格指数",
        "Productivity and Costs": "美国非农生产力与成本",
        "Job Openings and Labor Turnover Survey": "美国职位空缺与劳动力流动调查",
    }
    for prefix, translated in translations.items():
        if title.startswith(prefix):
            return translated
    return title


def raw_payload_from_fixture(content: bytes) -> RawPayload:
    return RawPayload(
        source_key=BlsCalendarAdapter.source_key,
        url=BlsCalendarAdapter.url,
        content=content,
        content_type="text/calendar",
    )
