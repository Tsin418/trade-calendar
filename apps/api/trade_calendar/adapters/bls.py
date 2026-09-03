import asyncio
import calendar
import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.errors import (
    AuthenticationError,
    NetworkError,
    ParseError,
    StructureChangedError,
)
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance

LONGBRIDGE_CALENDAR_URL = "https://open.longbridge.com/docs/market/calendar/macro-calendar"
EASTERN = ZoneInfo("America/New_York")
CalendarDocument = dict[str, Any]
CalendarRunner = Callable[[date, date], Awaitable[CalendarDocument]]


class BlsCalendarAdapter(SourceAdapter):
    """Read BLS-attributed releases through the authorized Longbridge CLI.

    Longbridge exposes multiple indicator rows for a single release. Headline,
    core, rate, and level rows are collapsed into one stable release event so
    the calendar creates one reminder for CPI, PPI, Employment Situation, and
    the other selected BLS release families.
    """

    source_key = "us_bls_calendar"
    version = "3.0.0"
    url = LONGBRIDGE_CALENDAR_URL

    def __init__(
        self,
        today: Callable[[], date] | None = None,
        now: Callable[[], datetime] | None = None,
        command_runner: CalendarRunner | None = None,
        cli_path: str = "longbridge",
    ) -> None:
        self.today = today or (lambda: datetime.now(UTC).date())
        self.now = now or (lambda: datetime.now(UTC))
        self.command_runner = command_runner or self._run_calendar_command
        self.cli_path = cli_path

    async def fetch(self) -> RawPayload:
        start = self.today() - timedelta(days=31)
        end = self.today() + timedelta(days=180)
        cursor = start
        groups: list[dict[str, Any]] = []
        queries: list[dict[str, object]] = []
        while cursor <= end:
            window_end = min(cursor + timedelta(days=12), end)
            document = await self.command_runner(cursor, window_end)
            rows = document.get("list") if isinstance(document, dict) else None
            if not isinstance(rows, list):
                raise StructureChangedError("Longbridge calendar list is missing")
            valid_groups = [row for row in rows if isinstance(row, dict)]
            groups.extend(valid_groups)
            queries.append({
                "start": cursor.isoformat(),
                "end": window_end.isoformat(),
                "groups": len(valid_groups),
            })
            cursor = window_end + timedelta(days=1)

        content = json.dumps({
            "provider": "Longbridge",
            "from": start.isoformat(),
            "to": end.isoformat(),
            "queries": queries,
            "list": groups,
        }, ensure_ascii=False).encode()
        return RawPayload(
            source_key=self.source_key,
            url=self.url,
            content=content,
            content_type="application/json",
        )

    async def _run_calendar_command(self, start: date, end: date) -> CalendarDocument:
        try:
            process = await asyncio.create_subprocess_exec(
                self.cli_path,
                "finance-calendar",
                "macrodata",
                "--market",
                "US",
                "--start",
                start.isoformat(),
                "--end",
                end.isoformat(),
                "--count",
                "200",
                "--star",
                "2",
                "--star",
                "3",
                "--format",
                "json",
                "--lang",
                "zh-CN",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise NetworkError("Longbridge CLI is unavailable") from exc
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45)
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise NetworkError("Longbridge calendar command timed out") from exc
        if process.returncode != 0:
            error_text = stderr.decode(errors="replace").casefold()
            if "not authenticated" in error_text or "auth token" in error_text:
                raise AuthenticationError("Longbridge CLI authentication is unavailable")
            raise NetworkError(
                f"Longbridge calendar command failed with exit code {process.returncode}"
            )
        try:
            document = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ParseError("invalid Longbridge calendar JSON") from exc
        if not isinstance(document, dict):
            raise StructureChangedError("Longbridge calendar response is not an object")
        return document

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        try:
            document = json.loads(payload.content)
        except json.JSONDecodeError as exc:
            raise ParseError("invalid aggregated Longbridge calendar JSON") from exc
        groups = document.get("list") if isinstance(document, dict) else None
        if not isinstance(groups, list):
            raise StructureChangedError("Longbridge calendar list is missing")

        grouped: dict[tuple[str, str], SourceEvent] = {}
        for group in groups:
            if not isinstance(group, dict):
                continue
            rows = group.get("infos")
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict) or str(row.get("market", "")).upper() != "US":
                    continue
                content = str(row.get("content") or "").strip()
                family = _classify_provider_event(content)
                if family is None:
                    continue
                try:
                    starts_at = _parse_timestamp(str(row["datetime"]))
                except (KeyError, TypeError, ValueError, OverflowError):
                    continue

                family_key, canonical_title = family
                ext_value = row.get("ext")
                ext: dict[str, Any] = ext_value if isinstance(ext_value, dict) else {}
                reference_period = _reference_period(
                    str(ext.get("period") or ""), starts_at, family_key
                )
                occurrence_key = (
                    reference_period or starts_at.astimezone(EASTERN).date().isoformat()
                )
                group_key = (family_key, occurrence_key)
                provider_id = str(row.get("id") or "").strip()
                detail = _indicator_detail(row, reference_period)
                existing = grouped.get(group_key)
                if existing is not None:
                    provider_ids = existing.raw.setdefault("provider_ids", [])
                    components = existing.raw.setdefault("components", [])
                    indicators = existing.raw.setdefault("indicators", [])
                    if provider_id and provider_id not in provider_ids:
                        provider_ids.append(provider_id)
                    if content and content not in components:
                        components.append(content)
                    indicators.append(detail)
                    continue

                event_type, importance = classify_bls_release(canonical_title)
                eastern_time = starts_at.astimezone(EASTERN)
                grouped[group_key] = SourceEvent(
                    source_event_id=f"longbridge:{family_key}:{_slug(occurrence_key)}",
                    title=canonical_title,
                    description=content or None,
                    starts_at=starts_at,
                    original_timezone="America/New_York",
                    original_time_text=eastern_time.strftime("%Y-%m-%d %H:%M ET"),
                    reference_period=reference_period,
                    status_text="completed" if starts_at <= self.now() else "expected",
                    url=LONGBRIDGE_CALENDAR_URL,
                    raw={
                        "provider": "Longbridge",
                        "family": family_key,
                        "event_type": event_type,
                        "importance": importance.value,
                        "provider_ids": [provider_id] if provider_id else [],
                        "components": [content] if content else [],
                        "indicators": [detail],
                    },
                )

        events = sorted(
            grouped.values(),
            key=lambda event: event.starts_at or datetime.max.replace(tzinfo=UTC),
        )
        if not events:
            raise StructureChangedError(
                "Longbridge calendar contained no recognized BLS release events"
            )
        return events

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        if event.starts_at is None:
            raise StructureChangedError("BLS calendar event is missing a timestamp")
        event_type, importance = classify_bls_release(event.title)
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh=translate_bls_title(event.title),
            title_original=event.title,
            institution="U.S. Bureau of Labor Statistics",
            country_code="US",
            category="macro_release",
            event_type=event_type,
            status=(
                EventStatus.COMPLETED
                if event.status_text == "completed"
                else EventStatus.EXPECTED
            ),
            importance=importance,
            date_precision=DatePrecision.MINUTE,
            starts_at=event.starts_at,
            original_timezone=event.original_timezone,
            original_time_text=event.original_time_text,
            reference_period=event.reference_period,
            market_tags=["US", "GLOBAL"],
            source_url=event.url or LONGBRIDGE_CALENDAR_URL,
            raw=event.raw,
        )


def _indicator_detail(row: dict[str, Any], reference_period: str | None) -> dict[str, Any]:
    values: dict[str, str] = {}
    data_values = row.get("data_kv")
    if isinstance(data_values, list):
        for value in data_values:
            if not isinstance(value, dict):
                continue
            value_type = str(value.get("type") or "").strip()
            if value_type in {"previous", "estimate", "actual"}:
                values[value_type] = str(value.get("value") or "")
    ext_value = row.get("ext")
    ext: dict[str, Any] = ext_value if isinstance(ext_value, dict) else {}
    return {
        "id": str(row.get("id") or ""),
        "content": str(row.get("content") or ""),
        "star": int(row.get("star") or 0),
        "period": reference_period,
        "unit": str(ext.get("unit") or ""),
        "values": values,
    }


def _classify_provider_event(content: str) -> tuple[str, str] | None:
    text = content.casefold()
    if re.search(r"\bjolts?\b|job openings|job quits|职位空缺|职位离职", text):
        return "job-openings-and-labor-turnover", "Job Openings and Labor Turnover Survey"
    if "employment cost index" in text or "就业成本指数" in text:
        return "employment-cost-index", "Employment Cost Index"
    if "real earnings" in text or "实际所得" in text or "实际收入" in text:
        return "real-earnings", "Real Earnings"
    if re.search(r"(?:import|export) prices?", text) or re.search(
        r"(?:进口|出口).*(?:价格|物价)", text
    ):
        return "import-export-prices", "U.S. Import and Export Price Indexes"
    if (
        "nonfarm productivity" in text
        or "unit labor cost" in text
        or "非农生产率" in text
        or "单位劳动力成本" in text
    ):
        if re.search(r"final|revised|修正值|终值", text):
            return "productivity-and-costs-final", "Productivity and Costs (R)"
        if re.search(r"prelim|preliminary|初值|初步", text):
            return "productivity-and-costs-preliminary", "Productivity and Costs (P)"
        return "productivity-and-costs", "Productivity and Costs"
    if ("cpi" in text or "consumer price" in text or "消费者价格指数" in text) and not (
        "cleveland fed" in text or "克里夫兰联储" in text
    ):
        return "consumer-price-index", "Consumer Price Index"
    if "ppi" in text or "producer price" in text or "生产者价格指数" in text:
        return "producer-price-index", "Producer Price Index"
    if (
        re.search(r"non[- ]?farm payroll", text)
        and re.search(r"annual revision|benchmark revision", text)
    ) or ("非农" in text and "年度" in text and "修" in text):
        return (
            "employment-situation-annual-revision",
            "Employment Situation Annual Benchmark Revision (P)",
        )
    if re.search(
        r"non[- ]?farm payroll|employment situation|average hourly earnings|"
        r"unemployment rate|labor force participation|average weekly hours|"
        r"非农就业|失业率|平均时薪|劳动参与率|平均每周工时",
        text,
    ):
        return "employment-situation", "The Employment Situation"
    return None


def _parse_timestamp(value: str) -> datetime:
    cleaned = value.strip()
    if cleaned.isdigit():
        return datetime.fromtimestamp(int(cleaned), tz=UTC)
    parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("calendar timestamp is missing timezone")
    return parsed.astimezone(UTC)


def _reference_period(
    value: str, starts_at: datetime, family_key: str | None = None
) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    iso_date = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", cleaned)
    if iso_date:
        year = int(iso_date.group(1))
        month_number = int(iso_date.group(2))
        if 1 <= month_number <= 12:
            if family_key and family_key.startswith("productivity-and-costs"):
                return f"Q{((month_number - 1) // 3) + 1} {year}"
            return f"{calendar.month_name[month_number]} {year}"
    iso_month = re.fullmatch(r"(\d{4})-(\d{1,2})", cleaned)
    if iso_month:
        year = int(iso_month.group(1))
        month_number = int(iso_month.group(2))
        if 1 <= month_number <= 12:
            return f"{calendar.month_name[month_number]} {year}"
    year_quarter = re.fullmatch(r"(\d{4})\s*Q([1-4])", cleaned, flags=re.IGNORECASE)
    if year_quarter:
        return f"Q{year_quarter.group(2)} {year_quarter.group(1)}"
    quarter_year = re.fullmatch(r"Q([1-4])\s*(\d{4})", cleaned, flags=re.IGNORECASE)
    if quarter_year:
        return f"Q{quarter_year.group(1)} {quarter_year.group(2)}"

    eastern_date = starts_at.astimezone(EASTERN).date()
    for month_number in range(1, 13):
        if cleaned.casefold() in {
            calendar.month_abbr[month_number].casefold(),
            calendar.month_name[month_number].casefold(),
        }:
            year = eastern_date.year - int(month_number > eastern_date.month)
            return f"{calendar.month_name[month_number]} {year}"
    quarter = re.fullmatch(r"Q([1-4])", cleaned, flags=re.IGNORECASE)
    if quarter:
        quarter_number = int(quarter.group(1))
        quarter_end_month = quarter_number * 3
        year = eastern_date.year - int(quarter_end_month > eastern_date.month)
        return f"Q{quarter_number} {year}"
    return cleaned


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def classify_bls_release(title: str) -> tuple[str, Importance]:
    lowered = title.casefold()
    rules: list[tuple[tuple[str, ...], str, Importance]] = [
        (("employment situation",), "employment", Importance.HIGH),
        (("consumer price index",), "inflation", Importance.HIGH),
        (("producer price index",), "inflation", Importance.HIGH),
        (("employment cost index",), "employment", Importance.MEDIUM),
        (("productivity",), "activity", Importance.MEDIUM),
        (("job openings",), "employment", Importance.MEDIUM),
        (("real earnings",), "employment", Importance.MEDIUM),
        (("import and export price",), "inflation", Importance.MEDIUM),
    ]
    for keywords, event_type, importance in rules:
        if any(keyword in lowered for keyword in keywords):
            return event_type, importance
    return "activity", Importance.MEDIUM


def translate_bls_title(title: str) -> str:
    translations: dict[str, str] = {
        "The Employment Situation": "美国就业报告",
        "Employment Situation Annual Benchmark Revision": "美国非农就业年度基准修订",
        "Consumer Price Index": "美国消费者价格指数",
        "Producer Price Index": "美国生产者价格指数",
        "Productivity and Costs": "美国非农生产力与成本",
        "Job Openings and Labor Turnover Survey": "美国职位空缺与劳动力流动调查",
        "Employment Cost Index": "美国就业成本指数",
        "Real Earnings": "美国实际工资",
        "U.S. Import and Export Price Indexes": "美国进出口价格指数",
    }
    for prefix, translated in translations.items():
        if title.startswith(prefix):
            if title.endswith("(P)"):
                return f"{translated}（初值）"
            if title.endswith("(R)"):
                return f"{translated}（修正值）"
            return translated
    return title


def raw_payload_from_fixture(content: bytes) -> RawPayload:
    return RawPayload(
        source_key=BlsCalendarAdapter.source_key,
        url=LONGBRIDGE_CALENDAR_URL,
        content=content,
        content_type="application/json",
    )
