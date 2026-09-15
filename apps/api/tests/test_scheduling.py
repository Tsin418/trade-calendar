from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import FetchRun, RunStatus, Source, SourceHealth
from trade_calendar.scheduling import enqueue_due_runs, enqueue_scheduled_run, refresh_stale_sources
from trade_calendar.sync import make_run


class StubAdapter(SourceAdapter):
    source_key = "scheduled-source"
    version = "test"

    async def fetch(self) -> RawPayload:
        raise NotImplementedError

    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        raise NotImplementedError

    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        raise NotImplementedError


async def add_source(
    session: AsyncSession,
    *,
    health: SourceHealth = SourceHealth.HEALTHY,
    enabled: bool = True,
    last_success_at: datetime | None = None,
) -> Source:
    source = Source(
        key="scheduled-source",
        name="Scheduled source",
        institution="Official institution",
        country_code="US",
        official_url="https://official.example",
        source_type="json",
        priority=10,
        enabled=enabled,
        health=health,
        schedule="0 * * * *",
        stale_after_hours=2,
        last_success_at=last_success_at,
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source


async def test_scheduled_run_is_idempotent_per_minute(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 9, 2, 5, 0, 31, tzinfo=UTC)
    async with session_factory() as session:
        await add_source(session, last_success_at=now)
        first, first_created = await enqueue_scheduled_run(
            session, "scheduled-source", StubAdapter(), now
        )
        second, second_created = await enqueue_scheduled_run(
            session, "scheduled-source", StubAdapter(), now + timedelta(seconds=20)
        )
    assert first_created is True
    assert second_created is False
    assert first is not None and second is not None and first.id == second.id


async def test_stale_refresh_uses_threshold_and_disables_inactive_source(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 9, 2, 5, 0, tzinfo=UTC)
    async with session_factory() as session:
        source = await add_source(session, last_success_at=now - timedelta(hours=3))
        changed = await refresh_stale_sources(session, now)
        await session.refresh(source)
        assert changed == 1
        assert source.health == SourceHealth.STALE

        source.enabled = False
        await session.commit()
        changed = await refresh_stale_sources(session, now)
        await session.refresh(source)
        assert changed == 1
        assert source.health == SourceHealth.DISABLED


@pytest.mark.parametrize("previous_status", [RunStatus.SUCCEEDED, RunStatus.FAILED])
async def test_recovery_coalesces_days_of_missed_runs_and_deduplicates_cron(
    session_factory: async_sessionmaker[AsyncSession], previous_status: RunStatus,
) -> None:
    now = datetime(2026, 9, 15, 3, 0, 10, tzinfo=UTC)
    adapter = StubAdapter()
    async with session_factory() as session:
        source = await add_source(session, last_success_at=now - timedelta(days=10))
        previous = make_run(source, adapter)
        previous.status = previous_status
        previous.created_at = now - timedelta(days=3)
        previous.finished_at = previous.created_at + timedelta(seconds=5)
        session.add(previous)
        await session.commit()

        recovered = await enqueue_due_runs(session, {source.key: adapter}, now)
        assert len(recovered) == 1
        assert recovered[0].trigger == "catchup"
        assert await enqueue_due_runs(session, {source.key: adapter}, now) == []
        assert await enqueue_due_runs(
            session, {source.key: adapter}, now + timedelta(minutes=1)
        ) == []
        _, created = await enqueue_scheduled_run(session, source.key, adapter, now)
        assert created is False
        assert await session.scalar(select(func.count()).select_from(FetchRun)) == 2


@pytest.mark.parametrize("previous_status", [RunStatus.SUCCEEDED, RunStatus.FAILED])
async def test_recovery_waits_for_next_schedule_after_a_completed_attempt(
    session_factory: async_sessionmaker[AsyncSession], previous_status: RunStatus,
) -> None:
    now = datetime(2026, 9, 15, 3, 0, tzinfo=UTC)
    adapter = StubAdapter()
    async with session_factory() as session:
        source = await add_source(session)
        previous = make_run(source, adapter)
        previous.status = previous_status
        previous.created_at = now - timedelta(hours=1)
        previous.finished_at = now - timedelta(minutes=30)
        session.add(previous)
        await session.commit()
        assert await enqueue_due_runs(
            session, {source.key: adapter}, now - timedelta(microseconds=1)
        ) == []
        assert len(await enqueue_due_runs(session, {source.key: adapter}, now)) == 1


@pytest.mark.parametrize("active_status", [RunStatus.PENDING, RunStatus.RUNNING])
async def test_recovery_and_cron_skip_active_manual_runs(
    session_factory: async_sessionmaker[AsyncSession], active_status: RunStatus,
) -> None:
    now = datetime(2026, 9, 15, 3, 0, tzinfo=UTC)
    adapter = StubAdapter()
    async with session_factory() as session:
        source = await add_source(session)
        active = make_run(source, adapter)
        active.status = active_status
        active.created_at = now - timedelta(hours=2)
        session.add(active)
        await session.commit()
        assert await enqueue_due_runs(session, {source.key: adapter}, now) == []
        _, created = await enqueue_scheduled_run(session, source.key, adapter, now)
        assert created is False


async def test_recovery_only_initializes_enabled_registered_sources(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 9, 15, 3, 0, tzinfo=UTC)
    adapter = StubAdapter()
    async with session_factory() as session:
        source = await add_source(session, enabled=False)
        assert await enqueue_due_runs(session, {source.key: adapter}, now) == []
        source.enabled = True
        await session.commit()
        assert await enqueue_due_runs(session, {}, now) == []
        runs = await enqueue_due_runs(session, {source.key: adapter}, now)
        assert len(runs) == 1
        assert runs[0].trigger == "initial"
