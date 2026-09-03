from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.adapters import (
    BeaScheduleAdapter,
    BlsCalendarAdapter,
    BojMeetingAdapter,
    BojReleaseScheduleAdapter,
    BokMeetingAdapter,
    FedFomcAdapter,
    HkexCalendarAdapter,
    HongKongStatisticsAdapter,
    HttpFetcher,
    KoreaStatisticsCalendarAdapter,
    SourceAdapter,
    TaiwanCbcMeetingAdapter,
    TaiwanStatisticsAdapter,
)
from trade_calendar.adapters.corporate import (
    FinnhubEarningsAdapter,
    JpxEarningsScheduleAdapter,
    KrxKindEarningsCallAdapter,
    LongbridgeEarningsAdapter,
    TwseEarningsCallAdapter,
)
from trade_calendar.core.config import Settings, get_settings
from trade_calendar.models.domain import Source, SourceHealth
from trade_calendar.watchlist import load_company_watchlist


def load_source_config(config_dir: Path) -> list[dict[str, Any]]:
    path = config_dir / "sources.yaml"
    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return list(document.get("sources", []))


def setting_is_configured(settings: Settings, name: str | None) -> bool:
    if not name:
        return True
    value = getattr(settings, name, None)
    if value is None:
        return False
    get_secret_value = getattr(value, "get_secret_value", None)
    if callable(get_secret_value):
        return bool(get_secret_value())
    return bool(value)


async def seed_sources(session: AsyncSession, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    count = 0
    for item in load_source_config(settings.config_dir):
        source = await session.scalar(select(Source).where(Source.key == item["id"]))
        required_setting = item.get("requires_setting")
        configured = setting_is_configured(settings, required_setting)
        values = {
            "name": item["name"],
            "institution": item["institution"],
            "country_code": item["country"],
            "official_url": item["official_url"],
            "source_type": item["type"],
            "priority": item["priority"],
            "enabled": item.get("enabled", True) and configured,
            "schedule": item["fetch_schedule"],
            "stale_after_hours": item["stale_after_hours"],
        }
        target_health = SourceHealth.STALE if values["enabled"] else SourceHealth.DISABLED
        if source is None:
            source = Source(key=item["id"], health=target_health, **values)
            session.add(source)
            count += 1
        else:
            for key, value in values.items():
                setattr(source, key, value)
            if not source.enabled:
                source.health = SourceHealth.DISABLED
            elif source.health == SourceHealth.DISABLED:
                source.health = SourceHealth.STALE
    manual = await session.scalar(select(Source).where(Source.key == "manual"))
    if manual:
        manual.enabled = False
        manual.health = SourceHealth.DISABLED
    await session.commit()
    return count


def adapter_registry(settings: Settings | None = None) -> dict[str, SourceAdapter]:
    settings = settings or get_settings()
    fetcher = HttpFetcher(user_agent="TradeCalendar/0.1 (+private single-user calendar)")
    companies = load_company_watchlist(settings.config_dir)
    registry: dict[str, SourceAdapter] = {
        "fed_fomc_calendar": FedFomcAdapter(fetcher),
        "us_bls_calendar": BlsCalendarAdapter(),
        "us_bea_schedule": BeaScheduleAdapter(fetcher),
        "boj_mpm": BojMeetingAdapter(fetcher),
        "boj_release_schedule": BojReleaseScheduleAdapter(fetcher),
        "bok_mpb": BokMeetingAdapter(fetcher),
        "korea_statistics_calendar": KoreaStatisticsCalendarAdapter(fetcher),
        "taiwan_cbc": TaiwanCbcMeetingAdapter(fetcher),
        "taiwan_dgbas_calendar": TaiwanStatisticsAdapter(fetcher),
        "hk_censtatd_schedule": HongKongStatisticsAdapter(fetcher),
        "hkex_calendar": HkexCalendarAdapter(fetcher),
        "jpx_earnings_schedule": JpxEarningsScheduleAdapter(fetcher, companies),
        "krx_kind_earnings_calls": KrxKindEarningsCallAdapter(fetcher, companies),
        "twse_earnings_calls": TwseEarningsCallAdapter(fetcher, companies),
        "longbridge_earnings": LongbridgeEarningsAdapter(companies),
    }
    if setting_is_configured(settings, "finnhub_api_key"):
        assert settings.finnhub_api_key is not None
        registry["finnhub_earnings"] = FinnhubEarningsAdapter(
            fetcher,
            settings.finnhub_api_key,
            companies,
        )
    return registry
