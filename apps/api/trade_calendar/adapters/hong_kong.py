import hashlib
import html
import json
import re
from datetime import UTC, date, datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import fitz
from selectolax.parser import HTMLParser

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import (
    ParseError,
    PayloadTooLargeError,
    StructureChangedError,
)
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance

HONG_KONG = ZoneInfo("Asia/Hong_Kong")
MONTH_NAMES = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


class HongKongStatisticsAdapter(SourceAdapter):
    source_key = "hk_censtatd_schedule"
    version = "1.0.0"
    url = "https://www.censtatd.gov.hk/en/press_release.html?selType=4"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self) -> RawPayload:
        listing = await self.fetcher.get(
            self.source_key, self.url, {"Accept": "text/html"}
        )
        tree = HTMLParser(listing.content)
        link = next(
            (
                node
                for node in tree.css("a")
                if ".pdf" in (node.attributes.get("href") or "").casefold()
                and "Schedule" in (node.attributes.get("href") or "")
            ),
            None,
        )
        href = link.attributes.get("href") if link is not None else None
        if not href:
            raise StructureChangedError("Hong Kong statistics schedule PDF link is missing")
        return await self.fetcher.get(
            self.source_key,
            urljoin(listing.url, href),
            {"Accept": "application/pdf"},
        )

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        try:
            document = fitz.open(stream=payload.content, filetype="pdf")
        except Exception as exc:
            raise ParseError("invalid Hong Kong statistics PDF") from exc
        if document.page_count > 10:
            raise PayloadTooLargeError(
                f"Hong Kong statistics PDF has {document.page_count} pages"
            )
        events: list[SourceEvent] = []
        for page in document:
            events.extend(parse_hong_kong_statistics_page(
                page.get_text("words", sort=True),
                page.get_text("text"),
                payload.url,
            ))
        if not events:
            raise StructureChangedError(
                "Hong Kong statistics PDF contained no recognizable release dates"
            )
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.starts_at is None:
            raise StructureChangedError("Hong Kong statistics release is missing a timestamp")
        event_type, importance = classify_hong_kong_statistic(event.title)
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh=translate_hong_kong_statistic(event.title),
            title_original=event.title,
            institution="Census and Statistics Department, HKSAR",
            country_code="HK",
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
            market_tags=["HK"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


class HkexCalendarAdapter(SourceAdapter):
    source_key = "hkex_calendar"
    version = "1.0.0"
    url = "https://www.hkex.com.hk/News/HKEX-Calendar?sc_lang=en"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self) -> RawPayload:
        return await self.fetcher.get(self.source_key, self.url, {"Accept": "text/html"})

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        try:
            page = payload.content.decode("utf-8")
            prefix = "var calendarDataSource = '"
            raw = page.split(prefix, 1)[1].split("';", 1)[0]
            document = json.loads(html.unescape(raw).replace("\\'", "'"))
        except (UnicodeDecodeError, IndexError, json.JSONDecodeError) as exc:
            raise ParseError("invalid HKEX embedded calendar JSON") from exc
        items = document.get("monthly")
        if not isinstance(items, list):
            raise StructureChangedError("HKEX monthly calendar is missing")
        events: list[SourceEvent] = []
        for item in items:
            if not isinstance(item, dict) or item.get("holidayIcon") != "HongKongPublicHolidays":
                continue
            try:
                local_date = date.fromisoformat(str(item["startdate"]))
            except (KeyError, ValueError):
                continue
            title = str(item.get("name") or "").strip()
            source_id = str(item.get("id") or "").strip("{} ")
            if not title or not source_id:
                continue
            events.append(SourceEvent(
                source_event_id=f"hkex-{source_id}",
                title=title,
                description=str(item.get("description") or "").strip() or None,
                local_date=local_date,
                original_timezone="Asia/Hong_Kong",
                original_time_text=local_date.isoformat(),
                url=payload.url,
                raw=item,
            ))
        if not events:
            raise StructureChangedError("HKEX calendar contained no Hong Kong market holidays")
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.local_date is None:
            raise StructureChangedError("HKEX holiday is missing a date")
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh=translate_hkex_holiday(event.title),
            title_original=event.title,
            institution="Hong Kong Exchanges and Clearing Limited",
            country_code="HK",
            category="market_calendar",
            event_type="market_holiday",
            status=(
                EventStatus.COMPLETED
                if event.local_date < datetime.now(HONG_KONG).date()
                else EventStatus.CONFIRMED
            ),
            importance=Importance.HIGH,
            date_precision=DatePrecision.DATE,
            local_date=event.local_date,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            market_tags=["HK"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


def parse_hong_kong_statistics_page(
    words: list[tuple[float, float, float, float, str, int, int, int]],
    text: str,
    source_url: str,
) -> list[SourceEvent]:
    year_match = re.search(r"Schedule of Regular Press Releases.*?\b(20\d{2})\b", text, re.S)
    if year_match is None:
        return []
    year = int(year_match.group(1))
    month_centers = {
        MONTH_NAMES[word]: (x0 + x1) / 2
        for x0, _y0, x1, _y1, word, *_rest in words
        if word in MONTH_NAMES
    }
    if len(month_centers) != 12:
        return []
    release_y = [
        y0
        for x0, y0, _x1, _y1, word, *_rest in words
        if word == "Release" and 290 <= x0 <= 370
    ]
    numeric = [
        (x0, y0, word)
        for x0, y0, _x1, _y1, word, *_rest in words
        if x0 >= 390
        and word.isdigit()
        and 1 <= int(word) <= 31
        and any(y0 <= anchor <= y0 + 16 for anchor in release_y)
    ]
    rows: list[list[tuple[float, float, str]]] = []
    for item in sorted(numeric, key=lambda value: (value[1], value[0])):
        if not rows or abs(rows[-1][0][1] - item[1]) > 2:
            rows.append([item])
        else:
            rows[-1].append(item)

    events: list[SourceEvent] = []
    for row in rows:
        row_y = row[0][1]
        title_words = [
            (y0, x0, word)
            for x0, y0, _x1, _y1, word, *_rest in words
            if x0 < 290
            and row_y + 5 <= y0 <= row_y + 45
            and re.search(r"[A-Za-z]", word)
        ]
        title = " ".join(word for _y, _x, word in sorted(title_words)).strip()
        if not title:
            continue
        digest = hashlib.sha256(title.encode()).hexdigest()[:14]
        for x0, _y0, day_text in row:
            month = min(
                month_centers,
                key=lambda value: abs(month_centers[value] - x0),
            )
            if abs(month_centers[month] - x0) > 35:
                continue
            try:
                local = datetime(
                    year,
                    month,
                    int(day_text),
                    16,
                    30,
                    tzinfo=HONG_KONG,
                )
            except ValueError:
                continue
            events.append(SourceEvent(
                source_event_id=f"hk-censtat-{digest}-{local:%Y%m%d}",
                title=title,
                starts_at=local.astimezone(UTC),
                original_timezone="Asia/Hong_Kong",
                original_time_text=f"{local:%Y-%m-%d 16:30} Asia/Hong_Kong",
                url=source_url,
                raw={"title": title, "release_date": local.date().isoformat()},
            ))
    return events


def classify_hong_kong_statistic(title: str) -> tuple[str, Importance]:
    lowered = title.casefold()
    if "consumer price" in lowered:
        return "inflation", Importance.HIGH
    if "gross domestic product" in lowered or "national income" in lowered:
        return "growth", Importance.HIGH
    if "unemployment" in lowered or "wage" in lowered or "persons engaged" in lowered:
        return "employment", Importance.HIGH
    if "trade" in lowered or "exports" in lowered or "imports" in lowered:
        return "trade", Importance.MEDIUM
    return "activity", Importance.MEDIUM


def translate_hong_kong_statistic(title: str) -> str:
    lowered = title.casefold()
    if "consumer price" in lowered:
        return "香港消费者物价指数"
    if "gross domestic product" in lowered:
        return "香港本地生产总值"
    if "unemployment" in lowered:
        return "香港失业及就业不足统计"
    if "retail sales" in lowered:
        return "香港零售业销售统计"
    return f"香港统计：{title}"


def translate_hkex_holiday(title: str) -> str:
    translations = {
        "National Day": "香港市场国庆日休市",
        "Christmas Day": "香港市场圣诞节休市",
        "Good Friday": "香港市场耶稣受难日休市",
        "Labour Day": "香港市场劳动节休市",
        "Ching Ming Festival": "香港市场清明节休市",
        "Tuen Ng Festival": "香港市场端午节休市",
    }
    return translations.get(title, f"香港市场休市：{title}")
