from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from trade_calendar.models.domain import Event, EventVersion
from trade_calendar.schemas.events import EventCreate, EventUpdate
from trade_calendar.services import create_event, lock_field, update_event


async def test_automatic_update_respects_field_lock(
    session_factory: async_sessionmaker[AsyncSession],
    minute_event_payload: dict[str, object],
) -> None:
    async with session_factory() as session:
        event, _ = await create_event(
            session, EventCreate.model_validate(minute_event_payload), "create-request"
        )
        await lock_field(session, event, "title_zh", "manual verification", "lock-request")
        event, changed = await update_event(
            session,
            event,
            EventUpdate(title_zh="Source overwrote this", notes="同步备注"),
            "sync-run",
            actor_type="source",
        )
        assert changed is True
        assert event.title_zh == "FOMC 利率决议"
        assert event.notes == "同步备注"
        versions = list(await session.scalars(
            select(EventVersion).where(EventVersion.event_id == event.id)
        ))
        assert len(versions) == 2


async def test_same_manual_update_does_not_create_version(
    session_factory: async_sessionmaker[AsyncSession],
    minute_event_payload: dict[str, object],
) -> None:
    async with session_factory() as session:
        event, _ = await create_event(
            session, EventCreate.model_validate(minute_event_payload), "create-request"
        )
        event, changed = await update_event(
            session, event, EventUpdate(importance=event.importance), "same-update"
        )
        assert changed is False
        assert event.current_version == 1
        count = len(list(await session.scalars(select(EventVersion))))
        assert count == 1


async def test_search_matches_notes(
    session_factory: async_sessionmaker[AsyncSession],
    minute_event_payload: dict[str, object],
) -> None:
    async with session_factory() as session:
        payload = dict(minute_event_payload, notes="观察日经期货波动")
        await create_event(session, EventCreate.model_validate(payload), "create-request")
        result = await session.scalar(select(Event).where(Event.notes.ilike("%日经%")))
        assert result is not None

