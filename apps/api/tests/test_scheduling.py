from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from trade_calendar.adapters.base import SourceAdapter
from trade_calendar.adapters.types import NormalizedEvent, RawPayload, SourceEvent
from trade_calendar.models.domain import Source, SourceHealth
from trade_calendar.scheduling import enqueue_scheduled_run, refresh_stale_sources


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
