import hashlib
import json
from datetime import UTC, datetime

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import ParseError, StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance


class BeaScheduleAdapter(SourceAdapter):
    source_key = "us_bea_schedule"
    version = "1.0.0"
    url = "https://apps.bea.gov/API/signup/release_dates.json"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self) -> RawPayload:
        return await self.fetcher.get(self.source_key, self.url, {"Accept": "application/json"})

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        try:
            document = json.loads(payload.content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParseError("invalid BEA release schedule JSON") from exc
        if not isinstance(document, dict):
            raise StructureChangedError("BEA schedule is not a JSON object")

        events: list[SourceEvent] = []
        seen: set[tuple[str, str]] = set()
        for title, details in document.items():
            if not isinstance(title, str) or not isinstance(details, dict):
                continue
            release_dates = details.get("release_dates")
            if not isinstance(release_dates, list):
                continue
            for value in release_dates:
                if not isinstance(value, str) or (title, value) in seen:
                    continue
                try:
                    starts_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if starts_at.tzinfo is None:
                    starts_at = starts_at.replace(tzinfo=UTC)
                starts_at = starts_at.astimezone(UTC)
                seen.add((title, value))
                digest = hashlib.sha256(title.encode()).hexdigest()[:16]
                events.append(SourceEvent(
                    source_event_id=f"bea-{digest}-{starts_at:%Y%m%dT%H%M}",
                    title=title.strip(),
                    starts_at=starts_at,
                    original_timezone="America/New_York",
                    original_time_text=value,
                    url=payload.url,
                    raw={"release": title, "release_date": value},
                ))
        if not events:
            raise StructureChangedError("BEA schedule contained no release dates")
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.starts_at is None:
            raise StructureChangedError("BEA release is missing a timestamp")
        event_type, importance = classify_bea_release(event.title)
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh=translate_bea_title(event.title),
            title_original=event.title,
            institution="U.S. Bureau of Economic Analysis",
            country_code="US",
            category="macro_release",
            event_type=event_type,
            status=(
                EventStatus.COMPLETED
                if event.starts_at < datetime.now(UTC)
                else EventStatus.CONFIRMED
            ),
            importance=importance,
            date_precision=DatePrecision.MINUTE,
            starts_at=event.starts_at,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            market_tags=["US", "GLOBAL"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


def classify_bea_release(title: str) -> tuple[str, Importance]:
    lowered = title.casefold()
    if "gross domestic product" in lowered:
        return "growth", Importance.HIGH
    if "personal income and outlays" in lowered:
        return "inflation", Importance.HIGH
    if "trade" in lowered or "international transactions" in lowered:
        return "trade", Importance.MEDIUM
    return "activity", Importance.MEDIUM


def translate_bea_title(title: str) -> str:
    translations = {
        "Gross Domestic Product": "美国国内生产总值",
        "Personal Income and Outlays": "美国个人收入与支出",
        "U.S. International Trade in Goods and Services": "美国国际商品与服务贸易",
        "U.S. International Transactions": "美国国际收支",
        "U.S. International Investment Position": "美国国际投资头寸",
    }
    return translations.get(title, f"美国 BEA：{title}")
