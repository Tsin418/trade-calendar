from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.models.domain import FetchRun, Source, SourceHealth
from trade_calendar.sync import make_run


async def enqueue_scheduled_run(
    session: AsyncSession,
    source_key: str,
    adapter: SourceAdapter,
    now: datetime | None = None,
) -> tuple[FetchRun | None, bool]:
    source = await session.scalar(select(Source).where(Source.key == source_key))
    if source is None or not source.enabled:
        return None, False
    timestamp = (now or datetime.now(UTC)).astimezone(UTC).replace(second=0, microsecond=0)
    run_key = f"{source.key}:scheduled:{timestamp:%Y-%m-%dT%H:%MZ}"
    existing = await session.scalar(select(FetchRun).where(FetchRun.run_key == run_key))
    if existing is not None:
        return existing, False
    run = make_run(source, adapter, trigger="scheduled")
    run.run_key = run_key
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run, True


async def refresh_stale_sources(
    session: AsyncSession, now: datetime | None = None
) -> int:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    sources = list(await session.scalars(select(Source)))
    changed = 0
    for source in sources:
        target = source.health
        if not source.enabled:
            target = SourceHealth.DISABLED
        elif source.health == SourceHealth.DISABLED:
            target = SourceHealth.STALE
        elif source.consecutive_failures == 0:
            if source.last_success_at is None:
                target = SourceHealth.STALE
            else:
                last_success = source.last_success_at
                if last_success.tzinfo is None:
                    last_success = last_success.replace(tzinfo=UTC)
                if current - last_success.astimezone(UTC) > timedelta(
                    hours=source.stale_after_hours
                ):
                    target = SourceHealth.STALE
        if target != source.health:
            source.health = target
            changed += 1
    if changed:
        await session.commit()
    return changed
