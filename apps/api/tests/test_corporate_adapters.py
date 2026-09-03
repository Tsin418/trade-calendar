import base64
import json
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.corporate import (
    FinnhubEarningsAdapter,
    JpxEarningsScheduleAdapter,
    KrxKindEarningsCallAdapter,
    LongbridgeEarningsAdapter,
    TwseEarningsCallAdapter,
)
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.core.config import Settings
from trade_calendar.models.domain import (
    DatePrecision,
    Event,
    EventSource,
    EventStatus,
    Importance,
    Source,
    SourceHealth,
)
from trade_calendar.source_registry import setting_is_configured
from trade_calendar.sync import SyncRunner, make_run
from trade_calendar.watchlist import WatchedCompany, load_company_watchlist


def company(
    *,
    key: str,
    ticker: str,
    market: str,
    name_zh: str,
    name_en: str,
    finnhub_symbol: str | None = None,
    longbridge_symbol: str | None = None,
    source_names: tuple[str, ...] = (),
) -> WatchedCompany:
    return WatchedCompany(
        key=key,
        ticker=ticker,
        market=market,
        name_zh=name_zh,
        name_en=name_en,
        finnhub_symbol=finnhub_symbol,
        longbridge_symbol=longbridge_symbol,
        source_names=(name_zh, name_en, *source_names),
        ir_url=None,
    )


def payload(source_key: str, content: bytes, url: str = "https://example.test") -> RawPayload:
    return RawPayload(
        source_key=source_key,
        url=url,
        content=content,
        content_type="application/json",
    )


def test_watchlist_contains_50_companies() -> None:
    config_dir = Path(__file__).resolve().parents[3] / "config"
    companies = load_company_watchlist(config_dir)
    assert len(companies) == 50
    assert {market: sum(item.market == market for item in companies) for market in {
        "US", "JP", "KR", "CN", "HK", "TW"
    }} == {"US": 10, "JP": 8, "KR": 8, "CN": 8, "HK": 8, "TW": 8}


def test_secret_setting_detects_non_empty_value() -> None:
    configured = Settings.model_construct(finnhub_api_key=SecretStr("configured"))
    missing = Settings.model_construct(finnhub_api_key=SecretStr(""))
    assert setting_is_configured(configured, "finnhub_api_key")
    assert not setting_is_configured(missing, "finnhub_api_key")


def test_finnhub_earnings_are_expected_date_events() -> None:
    apple = company(
        key="apple",
        ticker="AAPL",
        market="US",
        name_zh="苹果",
        name_en="Apple",
        finnhub_symbol="AAPL",
    )
    adapter = FinnhubEarningsAdapter(
        HttpFetcher(user_agent="test"),
        SecretStr("test-token"),
        [apple],
        today=lambda: date(2026, 9, 3),
    )
    document = {
        "earningsCalendar": [{
            "_company_key": "apple",
            "_query_symbol": "AAPL",
            "date": "2026-10-28",
            "hour": "amc",
            "quarter": 4,
            "year": 2026,
        }]
    }
    events = adapter.parse(payload(adapter.source_key, json.dumps(document).encode()))
    normalized = adapter.normalize(events[0])
    assert normalized.status == EventStatus.EXPECTED
    assert normalized.date_precision == DatePrecision.DATE
    assert normalized.local_date == date(2026, 10, 28)
    assert normalized.reference_period == "FY2026 Q4"
    assert normalized.tickers == ["AAPL"]
    assert normalized.original_time_text == "2026-10-28 after market close"


def test_longbridge_earnings_are_filtered_and_normalized_for_watchlist() -> None:
    apple = company(
        key="apple",
        ticker="AAPL",
        market="US",
        name_zh="苹果",
        name_en="Apple",
        longbridge_symbol="AAPL.US",
    )
    document = {"list": [{"date": "2026-10-28", "infos": [{
        "id": "12345",
        "symbol": "AAPL.US",
        "content": "FY2026 Q4 Earning Release",
        "counter_name": "Apple Inc.",
        "date": "2026.10.28 (EST)",
        "date_type": "Post",
        "ext": {
            "local_date": "2026-10-28",
            "financial_report": {
                "fiscal_year": "2026",
                "period": "4",
                "market_time": "after",
            },
        },
    }]}]}
    adapter = LongbridgeEarningsAdapter([apple], today=lambda: date(2026, 9, 3))
    events = adapter.parse(payload(
        adapter.source_key,
        json.dumps(document).encode(),
        adapter.url,
    ))
    normalized = adapter.normalize(events[0])
    assert normalized.local_date == date(2026, 10, 28)
    assert normalized.reference_period == "FY2026 Q4"
    assert normalized.tickers == ["AAPL"]
    assert normalized.original_time_text == "2026-10-28 after market close"


def test_jpx_workbook_filters_to_watchlist_and_confirms_date() -> None:
    toyota = company(
        key="toyota",
        ticker="7203",
        market="JP",
        name_zh="丰田汽车",
        name_en="Toyota Motor",
        finnhub_symbol="TM",
    )
    workbook = Workbook()
    sheet = workbook.active
    for _ in range(5):
        sheet.append([None] * 11)
    sheet.append([
        datetime(2026, 11, 5),
        7203,
        "トヨタ自動車",
        "TOYOTA MOTOR CORPORATION",
        datetime(2027, 3, 31),
        "輸送用機器",
        "Transportation Equipment",
        "第2四半期",
        "Second quarter",
        "プライム",
        "Prime",
    ])
    stream = BytesIO()
    workbook.save(stream)
    document = {"documents": [{
        "url": "https://www.jpx.co.jp/schedule.xlsx",
        "content": base64.b64encode(stream.getvalue()).decode(),
    }]}
    adapter = JpxEarningsScheduleAdapter(HttpFetcher(user_agent="test"), [toyota])
    events = adapter.parse(payload(adapter.source_key, json.dumps(document).encode()))
    normalized = adapter.normalize(events[0])
    assert normalized.status == EventStatus.CONFIRMED
    assert normalized.local_date == date(2026, 11, 5)
    assert normalized.reference_period == "FY2027 Q2"
    assert normalized.tickers == ["7203"]


def test_kind_ir_schedule_produces_exact_earnings_call_time() -> None:
    lg_energy = company(
        key="lg_energy_solution",
        ticker="373220",
        market="KR",
        name_zh="LG新能源",
        name_en="LG Energy Solution",
        finnhub_symbol="373220.KS",
        source_names=("LG에너지솔루션",),
    )
    html = """
    <table><tr>
      <td>1</td>
      <td><a title="LG에너지솔루션">LG에너지솔루션</a></td>
      <td><a onclick="fnDetailView('45959');">2026년 3분기 경영실적 발표</a></td>
      <td>Conference Call</td><td>2026-10-30</td><td>10:00</td>
    </tr></table>
    """
    adapter = KrxKindEarningsCallAdapter(
        HttpFetcher(user_agent="test"),
        [lg_energy],
        today=lambda: date(2026, 9, 3),
    )
    events = adapter.parse(payload(adapter.source_key, html.encode(), adapter.url))
    normalized = adapter.normalize(events[0])
    assert normalized.starts_at == datetime(2026, 10, 30, 1, 0, tzinfo=UTC)
    assert normalized.date_precision == DatePrecision.MINUTE
    assert normalized.reference_period == "FY2026 Q3"
    assert normalized.status == EventStatus.CONFIRMED
    assert normalized.tickers == ["373220"]


def test_twse_material_information_parses_roc_date_and_time() -> None:
    tsmc = company(
        key="tsmc",
        ticker="2330",
        market="TW",
        name_zh="台积电",
        name_en="TSMC",
        finnhub_symbol="TSM",
        source_names=("台積電",),
    )
    rows = [{
        "出表日期": "1150903",
        "公司代號": "2330",
        "公司名稱": "台積電",
        "主旨 ": "本公司召開2026年第三季法人說明會",
        "事實發生日": "1151015",
        "說明": (
            "1.召開法人說明會之日期：115/10/15\r\n"
            "2.召開法人說明會之時間：14 時 00 分\r\n"
            "4.法人說明會擇要訊息：2026年第三季財務結果"
        ),
    }]
    adapter = TwseEarningsCallAdapter(HttpFetcher(user_agent="test"), [tsmc])
    events = adapter.parse(payload(adapter.source_key, json.dumps(rows).encode(), adapter.url))
    normalized = adapter.normalize(events[0])
    assert normalized.starts_at == datetime(2026, 10, 15, 6, 0, tzinfo=UTC)
    assert normalized.reference_period == "FY2026 Q3"
    assert normalized.status == EventStatus.CONFIRMED
    assert normalized.tickers == ["2330"]


class FixtureCorporateAdapter(SourceAdapter):
    source_key = "fixture_corporate"
    version = "1.0.0"

    async def fetch(self) -> RawPayload:
        return payload(self.source_key, b"{}")

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        return [SourceEvent(
            source_event_id="apple-fy2026-q4",
            title="Apple Earnings Release",
            local_date=date(2026, 10, 28),
            reference_period="FY2026 Q4",
            url=payload.url,
        )]

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        return NormalizedEvent(
            source_event_id=event.source_event_id,
            title_zh="苹果财报发布",
            title_original=event.title,
            institution="Apple",
            country_code="US",
            category="corporate",
            event_type="earnings_release",
            status=EventStatus.EXPECTED,
            importance=Importance.HIGH,
            date_precision=DatePrecision.DATE,
            local_date=event.local_date,
            reference_period=event.reference_period,
            market_tags=["US"],
            tickers=["AAPL"],
            source_url=event.url or "https://example.test",
        )


async def test_sync_persists_source_tickers(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    adapter = FixtureCorporateAdapter()
    async with session_factory() as session:
        source = Source(
            key=adapter.source_key,
            name="Corporate Fixture",
            institution="Fixture",
            country_code="US",
            official_url="https://example.test",
            source_type="api",
            priority=10,
            enabled=True,
            health=SourceHealth.STALE,
            schedule="manual",
        )
        session.add(source)
        await session.commit()
        run = make_run(source, adapter)
        session.add(run)
        await session.commit()
        run_id = run.id

    result = await SyncRunner(session_factory).execute(run_id, adapter)
    assert result.created_count == 1
    async with session_factory() as session:
        stored = await session.scalar(select(Event))
        assert stored is not None
        assert stored.tickers == ["AAPL"]


class FlexibleCorporateAdapter(FixtureCorporateAdapter):
    def __init__(
        self,
        source_key: str,
        event_date: date,
        status: EventStatus,
    ) -> None:
        self.source_key = source_key
        self.event_date = event_date
        self.status = status

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        return [SourceEvent(
            source_event_id=f"{self.source_key}:apple-fy2026-q4",
            title="Apple Earnings Release",
            local_date=self.event_date,
            reference_period="FY2026 Q4",
            url=payload.url,
        )]

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        normalized = super().normalize(event)
        return normalized.model_copy(update={"status": self.status})


class ProviderLabeledCorporateAdapter(FlexibleCorporateAdapter):
    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        normalized = super().normalize(event)
        return normalized.model_copy(update={
            "title_original": "Apple Inc. Fiscal Fourth Quarter Results",
            "institution": "Apple Inc.",
        })


async def test_higher_priority_confirmation_wins_and_stays_primary(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    discovery = FlexibleCorporateAdapter(
        "earnings_discovery",
        date(2026, 10, 28),
        EventStatus.EXPECTED,
    )
    official = ProviderLabeledCorporateAdapter(
        "earnings_official",
        date(2026, 10, 29),
        EventStatus.CONFIRMED,
    )
    async with session_factory() as session:
        discovery_source = Source(
            key=discovery.source_key,
            name="Discovery",
            institution="Discovery",
            country_code="US",
            official_url="https://discovery.example",
            source_type="api",
            priority=60,
            enabled=True,
            health=SourceHealth.STALE,
            schedule="manual",
        )
        official_source = Source(
            key=official.source_key,
            name="Official",
            institution="Official",
            country_code="US",
            official_url="https://official.example",
            source_type="api",
            priority=10,
            enabled=True,
            health=SourceHealth.STALE,
            schedule="manual",
        )
        session.add_all([discovery_source, official_source])
        await session.commit()
        discovery_id = discovery_source.id
        official_id = official_source.id

    runner = SyncRunner(session_factory)
    for source_id, adapter in (
        (discovery_id, discovery),
        (official_id, official),
        (discovery_id, discovery),
    ):
        async with session_factory() as session:
            source = await session.get(Source, source_id)
            assert source is not None
            run = make_run(source, adapter)
            session.add(run)
            await session.commit()
            run_id = run.id
        await runner.execute(run_id, adapter)

    async with session_factory() as session:
        events = list(await session.scalars(select(Event)))
        assert len(events) == 1
        assert events[0].local_date == date(2026, 10, 29)
        assert events[0].status == EventStatus.CONFIRMED
        primary = await session.scalar(select(EventSource).where(EventSource.is_primary.is_(True)))
        assert primary is not None
        assert primary.source_id == official_id
