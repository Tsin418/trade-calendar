from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.adapters import BlsCalendarAdapter, FedFomcAdapter, HttpFetcher, SourceAdapter
from trade_calendar.core.config import Settings, get_settings
from trade_calendar.models.domain import Source, SourceHealth


def load_source_config(config_dir: Path) -> list[dict[str, Any]]:
    path = config_dir / "sources.yaml"
    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return list(document.get("sources", []))


async def seed_sources(session: AsyncSession, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    count = 0
    for item in load_source_config(settings.config_dir):
        source = await session.scalar(select(Source).where(Source.key == item["id"]))
        values = {
            "name": item["name"],
            "institution": item["institution"],
            "country_code": item["country"],
            "official_url": item["official_url"],
            "source_type": item["type"],
            "priority": item["priority"],
            "enabled": item.get("enabled", True),
            "schedule": item["fetch_schedule"],
            "stale_after_hours": item["stale_after_hours"],
        }
        if source is None:
            source = Source(key=item["id"], health=SourceHealth.STALE, **values)
            session.add(source)
            count += 1
        else:
            for key, value in values.items():
                setattr(source, key, value)
    manual = await session.scalar(select(Source).where(Source.key == "manual"))
    if manual:
        manual.enabled = False
        manual.health = SourceHealth.DISABLED
    await session.commit()
    return count


def adapter_registry(settings: Settings | None = None) -> dict[str, SourceAdapter]:
    settings = settings or get_settings()
    fetcher = HttpFetcher(user_agent="TradeCalendar/0.1 (+private single-user calendar)")
    return {
        "fed_fomc_calendar": FedFomcAdapter(fetcher),
        "us_bls_calendar": BlsCalendarAdapter(fetcher),
    }
