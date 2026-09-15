from datetime import UTC, datetime, timedelta

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.models.domain import FetchRun, RunStatus, Source, SourceHealth
from trade_calendar.sync import make_run


async def enqueue_scheduled_run(
    session: AsyncSession,
    source_key: str,
    adapter: SourceAdapter,
    now: datetime | None = None,
    *,
    only_if_due: bool = False,
) -> tuple[FetchRun | None, bool]:
    # Serialize cron and recovery checks for a source before inspecting its queue.
    source = await session.scalar(
        select(Source).where(Source.key == source_key).with_for_update()
    )
    if source is None or not source.enabled:
        return None, False
    current = (now or datetime.now(UTC)).astimezone(UTC)
    timestamp = current.replace(second=0, microsecond=0)
    run_key = f"{source.key}:scheduled:{timestamp:%Y-%m-%dT%H:%MZ}"
    existing = await session.scalar(select(FetchRun).where(FetchRun.run_key == run_key))
    if existing is not None:
        return existing, False
    active = await session.scalar(
        select(FetchRun).where(
            FetchRun.source_id == source.id,
            FetchRun.status.in_([RunStatus.PENDING, RunStatus.RUNNING]),
        ).order_by(FetchRun.created_at.desc()).limit(1)
    )
    if active is not None:
        return active, False
    trigger = "scheduled"
    if only_if_due:
        latest = await session.scalar(
            select(FetchRun).where(FetchRun.source_id == source.id)
            .order_by(FetchRun.created_at.desc()).limit(1)
        )
        if latest is not None:
            last_attempt = latest.finished_at or latest.started_at or latest.created_at
            if last_attempt.tzinfo is None:
                last_attempt = last_attempt.replace(tzinfo=UTC)
            next_due = CronTrigger.from_crontab(source.schedule, timezone="UTC").get_next_fire_time(
                None, last_attempt + timedelta(microseconds=1)
            )
            if next_due is None or next_due > current:
                return None, False
        trigger = "initial" if latest is None else "catchup"
    run = make_run(source, adapter, trigger=trigger)
    run.run_key = run_key
    run.created_at = current
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run, True


async def enqueue_due_runs(
    session: AsyncSession,
    registry: dict[str, SourceAdapter],
    now: datetime | None = None,
) -> list[FetchRun]:
    """Coalesce missed cron slots into one run, including after restart or sleep."""
    current = now or datetime.now(UTC)
    keys = list(await session.scalars(
        select(Source.key).where(Source.enabled.is_(True), Source.key.in_(registry))
        .order_by(Source.key)
    ))
    runs = []
    for key in keys:
        run, created = await enqueue_scheduled_run(
            session, key, registry[key], current, only_if_due=True
        )
        if created and run is not None:
            runs.append(run)
    await session.commit()
    return runs


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
