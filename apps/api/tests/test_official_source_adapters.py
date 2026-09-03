import json
from datetime import UTC, date, datetime
from pathlib import Path

from trade_calendar.adapters.bea import BeaScheduleAdapter
from trade_calendar.adapters.boj import (
    BojMeetingAdapter,
    BojReleaseScheduleAdapter,
    parse_boj_release_rows,
)
from trade_calendar.adapters.bok import BokMeetingAdapter
from trade_calendar.adapters.hong_kong import (
    HkexCalendarAdapter,
    HongKongStatisticsAdapter,
    parse_hong_kong_statistics_page,
)
from trade_calendar.adapters.http import HttpFetcher
from trade_calendar.adapters.korea import KoreaStatisticsCalendarAdapter
from trade_calendar.adapters.taiwan import TaiwanCbcMeetingAdapter, TaiwanStatisticsAdapter
from trade_calendar.adapters.types import RawPayload
from trade_calendar.core.config import Settings
from trade_calendar.models.domain import DatePrecision
from trade_calendar.source_registry import (
    adapter_registry,
    load_source_config,
    setting_is_configured,
)


def payload(source_key: str, content: str, content_type: str = "text/html") -> RawPayload:
    return RawPayload(
        source_key=source_key,
        url=f"https://official.example/{source_key}",
        content=content.encode(),
        content_type=content_type,
    )


def fetcher() -> HttpFetcher:
    return HttpFetcher(user_agent="test-suite")


def test_registry_covers_every_enabled_configured_source() -> None:
    config_dir = Path(__file__).resolve().parents[3] / "config"
    settings = Settings(_env_file=None, config_dir=config_dir)
    enabled = {
        item["id"]
        for item in load_source_config(config_dir)
        if item.get("enabled", True)
        and (
            setting_is_configured(settings, item.get("requires_setting"))
        )
    }
    assert enabled == set(adapter_registry(settings))


def test_bea_machine_readable_schedule() -> None:
    adapter = BeaScheduleAdapter(fetcher())
    document = {
        "Gross Domestic Product": {
            "release_dates": [
                "2026-09-30T12:30:00+00:00",
                "2026-09-30T12:30:00+00:00",
            ]
        },
        "Personal Income and Outlays": {
            "release_dates": ["2026-10-29T12:30:00+00:00"]
        },
    }
    events = adapter.parse(payload(adapter.source_key, json.dumps(document), "application/json"))
    normalized = [adapter.normalize(event) for event in events]
    assert len(normalized) == 2
    assert normalized[0].event_type == "growth"
    assert normalized[0].starts_at == datetime(2026, 9, 30, 12, 30, tzinfo=UTC)


def test_boj_meeting_and_release_schedules() -> None:
    meeting = BojMeetingAdapter(fetcher())
    html = """
    <h2>2026</h2><table><tr><th>Date of MPM</th></tr>
    <tr><td>Sept. 17 (Thurs.), 18 (Fri.)</td></tr></table>
    <h2>2027</h2><table><tr><td>Jan. 21 (Thurs.), 22 (Fri.)</td></tr></table>
    """
    events = meeting.parse(payload(meeting.source_key, html))
    assert [event.local_date for event in events] == [date(2026, 9, 18), date(2027, 1, 22)]

    rows = [
        ["Date", "Time", "Title"],
        ["Sept. 18", "undecided", "Statement on Monetary Policy"],
        ["", "14:00", "Indicators for Core CPI"],
        ["24", "around 17:00", "Japanese Government Bonds Held by the Bank of Japan"],
    ]
    releases = parse_boj_release_rows(
        rows, date(2026, 9, 2), "https://www.boj.or.jp/en/about/calendar/index.htm"
    )
    assert releases[0].local_date == date(2026, 9, 18)
    assert releases[1].starts_at == datetime(2026, 9, 18, 5, 0, tzinfo=UTC)
    assert releases[2].starts_at == datetime(2026, 9, 24, 8, 0, tzinfo=UTC)

    release_adapter = BojReleaseScheduleAdapter(fetcher())
    normalized = release_adapter.normalize(releases[0])
    assert normalized.event_type == "central_bank_decision"
    assert normalized.date_precision == DatePrecision.DATE


def test_bok_current_year_meeting_table() -> None:
    adapter = BokMeetingAdapter(fetcher())
    html = """
    <h3>2026</h3><table>
      <tr><th>Jan.</th><th>Feb.</th></tr>
      <tr><td>Jan.15 (Thu)</td><td>Feb.26 (Thu)</td></tr>
    </table>
    """
    events = adapter.parse(payload(adapter.source_key, html))
    assert [event.local_date for event in events] == [date(2026, 1, 15), date(2026, 2, 26)]
    assert adapter.normalize(events[0]).title_zh == "韩国央行利率决议"


def test_korea_release_plan_parses_full_official_schedule() -> None:
    html = """
    <h3>2026년 전체 보도계획</h3>
    <table><tbody>
      <tr class="tr-notice"><td>09.02.( 수 )</td><td>08:00</td>
        <td>2026년 8월 소비자물가동향</td><td>물가동향과</td><td></td></tr>
      <tr class="tr-notice"><td>09.09.( 수 )</td><td>08:00</td>
        <td>2026년 8월 고용동향</td><td>고용통계과</td><td></td></tr>
    </tbody></table>
    """
    adapter = KoreaStatisticsCalendarAdapter(
        fetcher(),
        today=lambda: date(2026, 9, 3),
        now=lambda: datetime(2026, 9, 3, tzinfo=UTC),
    )
    events = adapter.parse(payload(adapter.source_key, html))
    assert len(events) == 2
    inflation = adapter.normalize(events[0])
    employment = adapter.normalize(events[1])
    assert inflation.starts_at == datetime(2026, 9, 1, 23, 0, tzinfo=UTC)
    assert inflation.title_zh == "韩国消费者物价指数"
    assert inflation.reference_period == "2026-08"
    assert employment.title_zh == "韩国就业数据"
    assert employment.status.value == "confirmed"


def test_taiwan_central_bank_announcement() -> None:
    adapter = TaiwanCbcMeetingAdapter(fetcher())
    html = """
    <h1>Provisional Schedule of Monetary Policy Meetings for 2026</h1>
    <p>The Bank announces the provisional schedule of Monetary Policy Meetings for 2026:</p>
    <p>March 19</p><p>June 18</p><p>September 17</p><p>December 17</p>
    <p>A news conference will take place after each meeting.</p>
    """
    events = adapter.parse(payload(adapter.source_key, html))
    assert len(events) == 4
    assert events[-1].local_date == date(2026, 12, 17)


def test_taiwan_statistics_embedded_json() -> None:
    adapter = TaiwanStatisticsAdapter(fetcher())
    item = {
        "ContentUrl": "https://eng.stat.gov.tw/item?MetaI_D=149&year=2026",
        "DeptName": "DGBAS",
        "name": "Compilation of Consumer Price Index",
        "category": "Compilation of Consumer Price Index",
        "timedatas": [[{"date": "8", "time": "16:00", "notice": "(Dec 2025)"}]]
        + [[] for _ in range(11)],
    }
    document = {"year": 2026, "list": [item]}
    html = f"<script>var VueData = {json.dumps(document)};var app = true;</script>"
    events = adapter.parse(payload(adapter.source_key, html))
    normalized = adapter.normalize(events[0])
    assert normalized.starts_at == datetime(2026, 1, 8, 8, 0, tzinfo=UTC)
    assert normalized.event_type == "inflation"
    assert normalized.reference_period == "(Dec 2025)"


def test_taiwan_services_producer_prices_keep_distinct_title() -> None:
    adapter = TaiwanStatisticsAdapter(fetcher())
    html = """
    <script>var VueData = {"year":2026,"list":[{
      "ContentUrl":"https://eng.stat.gov.tw/item?MetaI_D=1984",
      "DeptName":"DGBAS",
      "name":"Services Producer Price Indices",
      "category":"Compilation of Producer Price Index",
      "timedatas":[[],[],[],[],[],[],[],[],[
        {"date":"8","time":"16:00","notice":"(Jul 2026)"}
      ],[],[],[]]
    }]};var app = true;</script>
    """
    event = adapter.normalize(adapter.parse(payload(adapter.source_key, html))[0])
    assert event.title_zh == "台湾服务业生产者物价指数"


def test_hkex_embedded_calendar_filters_to_hong_kong_holidays() -> None:
    adapter = HkexCalendarAdapter(fetcher())
    document = {
        "monthly": [
            {
                "id": "{holiday}",
                "name": "National Day",
                "description": "Hong Kong Market is closed",
                "startdate": "2026-10-01",
                "holidayIcon": "HongKongPublicHolidays",
            },
            {
                "id": "{listing}",
                "name": "New listing",
                "startdate": "2026-10-02",
                "holidayIcon": "",
            },
        ]
    }
    html = f"<script>var calendarDataSource = '{json.dumps(document)}';</script>"
    events = adapter.parse(payload(adapter.source_key, html))
    assert len(events) == 1
    assert adapter.normalize(events[0]).event_type == "market_holiday"


def test_hong_kong_statistics_pdf_coordinate_parser() -> None:
    words: list[tuple[float, float, float, float, str, int, int, int]] = []
    for month, x in zip(
        [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        range(415, 1076, 60),
        strict=True,
    ):
        words.append((float(x), 198.0, float(x + 20), 211.0, month, 0, 0, 0))
    words.extend([
        (322.0, 312.0, 348.0, 324.0, "Release", 0, 0, 0),
        (415.0, 300.0, 426.0, 313.0, "20", 0, 0, 0),
        (475.0, 300.0, 486.0, 313.0, "21", 0, 0, 0),
        (54.0, 312.0, 121.0, 324.0, "Unemployment", 0, 0, 0),
        (124.0, 312.0, 140.0, 324.0, "and", 0, 0, 0),
        (143.0, 312.0, 222.0, 324.0, "underemployment", 0, 0, 0),
        (54.0, 323.0, 92.0, 336.0, "statistics", 0, 0, 0),
    ])
    events = parse_hong_kong_statistics_page(
        words,
        "Schedule of Regular Press Releases on Statistical Data in 2026",
        "https://www.censtatd.gov.hk/schedule.pdf",
    )
    assert [event.starts_at for event in events] == [
        datetime(2026, 1, 20, 8, 30, tzinfo=UTC),
        datetime(2026, 2, 21, 8, 30, tzinfo=UTC),
    ]
    adapter = HongKongStatisticsAdapter(fetcher())
    assert adapter.normalize(events[0]).event_type == "employment"
