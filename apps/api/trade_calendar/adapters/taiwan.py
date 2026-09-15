import hashlib
import html
import json
import re
from collections.abc import Callable
from datetime import UTC, date, datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from selectolax.parser import HTMLParser

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import ParseError, StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance

TAIPEI = ZoneInfo("Asia/Taipei")
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


class TaiwanCbcMeetingAdapter(SourceAdapter):
    source_key = "taiwan_cbc"
    version = "1.1.0"
    url = "https://www.cbc.gov.tw/en/lp-448-2-1-20.html"
    max_listing_pages = 20

    def __init__(self, fetcher: HttpFetcher, today: Callable[[], date] | None = None) -> None:
        self.fetcher = fetcher
        self.today = today or (lambda: datetime.now(TAIPEI).date())

    async def fetch(self) -> RawPayload:
        year = self.today().year
        links: dict[int, str] = {}
        listing_url = self.url
        for page in range(1, self.max_listing_pages + 1):
            listing = await self.fetcher.get(
                self.source_key, listing_url, {"Accept": "text/html"}
            )
            tree = HTMLParser(listing.content)
            next_url = None
            for node in tree.css("a[href]"):
                href = urljoin(listing.url, node.attributes["href"])
                label = node.text(separator=" ", strip=True)
                match = re.search(
                    r"Schedule of Monetary Policy Meetings for\s+(20\d{2})", label, re.I
                )
                if match and int(match.group(1)) in {year, year + 1}:
                    links.setdefault(int(match.group(1)), href)
                # Follow only the next official listing page, never an arbitrary link.
                if href == f"https://www.cbc.gov.tw/en/lp-448-2-{page + 1}-20.html":
                    next_url = href
            if year in links or next_url is None:
                break
            listing_url = next_url
        if year not in links:
            raise StructureChangedError(
                f"Taiwan CBC meeting schedule for {year} is missing from the press release index"
            )
        announcements = []
        for announcement_year, url in sorted(links.items()):
            document = await self.fetcher.get(self.source_key, url, {"Accept": "text/html"})
            announcements.append({
                "year": announcement_year, "url": document.url,
                "html": document.content.decode("utf-8"),
            })
        return RawPayload(
            source_key=self.source_key,
            url=links[year],
            content=json.dumps({"announcements": announcements}, ensure_ascii=False).encode(),
            content_type="application/json",
        )

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        if payload.content_type == "application/json":
            combined: list[SourceEvent] = []
            for document in json.loads(payload.content)["announcements"]:
                combined.extend(self.parse(RawPayload(
                    source_key=self.source_key, url=document["url"],
                    content=document["html"].encode(), content_type="text/html",
                )))
            return combined
        tree = HTMLParser(payload.content)
        body = tree.body
        text = re.sub(
            r"\s+", " ", body.text(separator=" ", strip=True) if body is not None else ""
        )
        year_match = re.search(r"Monetary Policy Meetings for (20\d{2})", text, re.I)
        marker = re.search(
            r"announces the provisional schedule of Monetary Policy Meetings", text, re.I
        )
        if year_match is None or marker is None:
            raise StructureChangedError("Taiwan CBC meeting announcement structure changed")
        section = text[marker.end():]
        section = re.split(r"A news conference", section, maxsplit=1, flags=re.I)[0]
        year = int(year_match.group(1))
        events: list[SourceEvent] = []
        for month_name, day_text in re.findall(
            r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})\b", section, re.I
        ):
            meeting_date = date(year, MONTHS[month_name.casefold()], int(day_text))
            events.append(SourceEvent(
                source_event_id=f"taiwan-cbc-{meeting_date.isoformat()}",
                title="Taiwan Central Bank Monetary Policy Meeting",
                local_date=meeting_date,
                original_timezone="Asia/Taipei",
                original_time_text=f"{month_name} {day_text}, {year}",
                url=payload.url,
                raw={"meeting_date": meeting_date.isoformat(), "provisional": True},
            ))
        if not events:
            raise StructureChangedError("Taiwan CBC announcement contained no meeting dates")
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.local_date is None:
            raise StructureChangedError("Taiwan CBC meeting is missing a decision date")
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh="台湾央行利率决议",
            title_original=event.title,
            institution="Central Bank of the Republic of China (Taiwan)",
            country_code="TW",
            category="monetary_policy",
            event_type="central_bank_decision",
            status=(
                EventStatus.COMPLETED
                if event.local_date < datetime.now(TAIPEI).date()
                else EventStatus.PROVISIONAL
            ),
            importance=Importance.CRITICAL,
            date_precision=DatePrecision.DATE,
            local_date=event.local_date,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            market_tags=["TW", "GLOBAL"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


class TaiwanStatisticsAdapter(SourceAdapter):
    source_key = "taiwan_dgbas_calendar"
    version = "1.0.0"
    url = "https://eng.stat.gov.tw/News_NoticeCalendar_EN.aspx?n=4011&page=1&PageSize=100"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self) -> RawPayload:
        return await self.fetcher.get(self.source_key, self.url, {"Accept": "text/html"})

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        try:
            page = payload.content.decode("utf-8")
            raw = html.unescape(page.split("var VueData = ", 1)[1])
            document, _ = json.JSONDecoder().raw_decode(raw)
        except (UnicodeDecodeError, IndexError, json.JSONDecodeError) as exc:
            raise ParseError("invalid Taiwan statistics calendar data") from exc
        year = document.get("year")
        items = document.get("list")
        if not isinstance(year, int) or not isinstance(items, list):
            raise StructureChangedError("Taiwan statistics calendar fields are missing")

        events: list[SourceEvent] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("name") or "").strip()
            content_url = str(item.get("ContentUrl") or payload.url)
            meta_match = re.search(r"MetaI_D=(\d+)", content_url)
            item_key = meta_match.group(1) if meta_match else hashlib.sha256(
                title.encode()
            ).hexdigest()[:16]
            timedatas = item.get("timedatas")
            if not title or not isinstance(timedatas, list):
                continue
            for month, entries in enumerate(timedatas[:12], start=1):
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    try:
                        day = int(str(entry.get("date") or ""))
                        hour, minute = map(int, str(entry.get("time")).split(":"))
                        local = datetime(year, month, day, hour, minute, tzinfo=TAIPEI)
                    except (TypeError, ValueError):
                        continue
                    starts_at = local.astimezone(UTC)
                    events.append(SourceEvent(
                        source_event_id=f"dgbas-{item_key}-{local:%Y%m%dT%H%M}",
                        title=title,
                        starts_at=starts_at,
                        original_timezone="Asia/Taipei",
                        original_time_text=f"{local:%Y-%m-%d %H:%M} Asia/Taipei",
                        reference_period=str(entry.get("notice") or "").strip() or None,
                        url=content_url,
                        raw={
                            "department": item.get("DeptName"),
                            "category": item.get("category"),
                            "date": local.isoformat(),
                            "notice": entry.get("notice"),
                        },
                    ))
        if not events:
            raise StructureChangedError("Taiwan statistics calendar contained no release dates")
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.starts_at is None:
            raise StructureChangedError("Taiwan statistics release is missing a timestamp")
        event_type, importance = classify_taiwan_release(event.title)
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh=translate_taiwan_title(event.title),
            title_original=event.title,
            institution="Directorate-General of Budget, Accounting and Statistics",
            country_code="TW",
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
            reference_period=event.reference_period,
            market_tags=["TW"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


def classify_taiwan_release(title: str) -> tuple[str, Importance]:
    lowered = title.casefold()
    if "consumer price" in lowered or "producer price" in lowered:
        return "inflation", Importance.HIGH
    if "national accounts" in lowered or "gross domestic product" in lowered:
        return "growth", Importance.HIGH
    if "labor force" in lowered or "unemploy" in lowered or "employee" in lowered:
        return "employment", Importance.HIGH
    if "import" in lowered or "export" in lowered or "trade" in lowered:
        return "trade", Importance.MEDIUM
    return "activity", Importance.MEDIUM


def translate_taiwan_title(title: str) -> str:
    lowered = title.casefold()
    if "consumer price" in lowered:
        return "台湾消费者物价指数"
    if "services producer price" in lowered:
        return "台湾服务业生产者物价指数"
    if "producer price" in lowered:
        return "台湾生产者物价指数"
    if "national accounts" in lowered or "gross domestic product" in lowered:
        return "台湾国民生产与所得统计"
    if "labor force" in lowered or "unemploy" in lowered:
        return "台湾就业与失业统计"
    return f"台湾统计：{title}"
