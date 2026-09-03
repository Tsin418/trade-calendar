import hashlib
import re
from collections.abc import Callable
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from selectolax.parser import HTMLParser

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import StructureChangedError
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance

SEOUL = ZoneInfo("Asia/Seoul")
KOREA_RELEASE_PLAN_URL = (
    "https://mods.go.kr/newsPln.es?mid=a10305000000&oa_mm=ALL"
)


class KoreaStatisticsCalendarAdapter(SourceAdapter):
    source_key = "korea_statistics_calendar"
    version = "1.0.0"
    url = KOREA_RELEASE_PLAN_URL

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
        return await self.fetcher.get(
            self.source_key,
            self.url,
            {"Accept": "text/html"},
        )

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        tree = HTMLParser(payload.content)
        heading = next(
            (
                node.text(separator=" ", strip=True)
                for node in tree.css("h3")
                if "보도계획" in node.text()
            ),
            "",
        )
        year_match = re.search(r"(20\d{2})년", heading)
        year = int(year_match.group(1)) if year_match else self.today().year
        events: dict[str, SourceEvent] = {}
        for row in tree.css("tr.tr-notice, table tbody tr"):
            cells = row.css("td")
            if len(cells) < 3:
                continue
            date_text = cells[0].text(separator=" ", strip=True)
            date_match = re.search(r"(\d{1,2})\.(\d{1,2})\.", date_text)
            time_text = cells[1].text(separator=" ", strip=True)
            time_match = re.search(r"(\d{1,2}):(\d{2})", time_text)
            title = cells[2].text(separator=" ", strip=True)
            if date_match is None or time_match is None or not title:
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
            department = (
                cells[3].text(separator=" ", strip=True) if len(cells) > 3 else ""
            )
            identity = f"{local.isoformat()}|{title}"
            digest = hashlib.sha256(identity.encode()).hexdigest()[:20]
            source_id = f"mods-{digest}"
            events[source_id] = SourceEvent(
                source_event_id=source_id,
                title=title,
                starts_at=local.astimezone(UTC),
                original_timezone="Asia/Seoul",
                original_time_text=f"{local:%Y-%m-%d %H:%M} Asia/Seoul",
                reference_period=extract_korean_reference_period(title),
                status_text=(
                    "completed" if local.astimezone(UTC) < self.now() else "confirmed"
                ),
                url=payload.url,
                raw={
                    "department": department,
                    "release_date": local.date().isoformat(),
                    "release_time": f"{local:%H:%M}",
                    "title_ko": title,
                },
            )
        if not events:
            raise StructureChangedError(
                "Korea release plan contained no recognizable schedule rows"
            )
        return list(events.values())

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.starts_at is None:
            raise StructureChangedError("Korea statistics release is missing a timestamp")
        event_type, importance = classify_korean_release(event.title)
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh=translate_korean_title(event.title),
            title_original=event.title,
            institution="Ministry of Data and Statistics, Republic of Korea",
            country_code="KR",
            category="macro_release",
            event_type=event_type,
            status=(
                EventStatus.COMPLETED
                if event.starts_at < self.now()
                else EventStatus.CONFIRMED
            ),
            importance=importance,
            date_precision=DatePrecision.MINUTE,
            starts_at=event.starts_at,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            reference_period=event.reference_period,
            market_tags=["KR"],
            source_url=event.url or self.url,
            raw=event.raw,
        )


def classify_korean_release(title: str) -> tuple[str, Importance]:
    if "소비자물가" in title or "물가동향" in title:
        return "inflation", Importance.HIGH
    if "고용동향" in title or "실업" in title:
        return "employment", Importance.HIGH
    if "국내총생산" in title or "지역내총생산" in title or "경제성장" in title:
        return "growth", Importance.HIGH
    if "무역" in title or "수출" in title or "수입" in title:
        return "trade", Importance.MEDIUM
    if "산업활동" in title or "생산량" in title or "온라인쇼핑" in title:
        return "activity", Importance.MEDIUM
    return "activity", Importance.LOW


def translate_korean_title(title: str) -> str:
    translations = (
        ("소비자물가동향", "韩国消费者物价指数"),
        ("고용동향", "韩国就业数据"),
        ("산업활동동향", "韩国工业活动数据"),
        ("온라인쇼핑동향", "韩国网络购物趋势"),
        ("국내인구이동통계", "韩国国内人口迁移统计"),
        ("인구동향", "韩国人口趋势"),
        ("가계동향조사", "韩国家庭收支调查"),
        ("지역경제동향", "韩国地区经济趋势"),
    )
    for needle, translated in translations:
        if needle in title:
            return translated
    return f"韩国统计发布：{title}"


def extract_korean_reference_period(title: str) -> str | None:
    month = re.search(r"(20\d{2})년\s*(\d{1,2})월", title)
    if month:
        return f"{month.group(1)}-{int(month.group(2)):02d}"
    quarter = re.search(r"(20\d{2})년\s*([1-4])/4분기", title)
    if quarter:
        return f"{quarter.group(1)} Q{quarter.group(2)}"
    year = re.search(r"(20\d{2})년", title)
    return year.group(1) if year else None
