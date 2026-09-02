from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import delete, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.core.database import get_session
from trade_calendar.core.errors import ApiError
from trade_calendar.models.base import utc_now
from trade_calendar.models.domain import AuditLog, Event, EventChange, EventFieldLock, EventVersion
from trade_calendar.schemas.events import (
    ChangeRead,
    EventCreate,
    EventList,
    EventRead,
    EventUpdate,
    FieldLockCreate,
    FieldLockRead,
    VersionRead,
)
from trade_calendar.services import (
    count_events,
    create_event,
    event_query,
    get_event_or_404,
    lock_field,
    soft_delete_event,
    update_event,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventList)
async def list_events(
    from_at: datetime | None = Query(default=None, alias="from"),
    to_at: datetime | None = Query(default=None, alias="to"),
    from_date: date | None = None,
    to_date: date | None = None,
    country: str | None = None,
    market: str | None = None,
    category: str | None = None,
    importance: str | None = None,
    event_status: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> EventList:
    statement = event_query(
        from_at=from_at, to_at=to_at, from_date=from_date, to_date=to_date,
        country=country, market=market, category=category,
        importance=importance, status=event_status, query=q,
    )
    total = await count_events(session, statement)
    rows = await session.scalars(
        statement.order_by(
            nulls_last(Event.starts_at.asc()),
            nulls_last(Event.local_date.asc()),
            Event.importance.asc(),
            Event.id.asc(),
        ).limit(limit).offset(offset)
    )
    return EventList(
        items=[EventRead.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def post_event(
    payload: EventCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    event, created = await create_event(session, payload, request.state.request_id)
    if not created:
        response.status_code = status.HTTP_200_OK
    return EventRead.model_validate(event)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(event_id: UUID, session: AsyncSession = Depends(get_session)) -> EventRead:
    return EventRead.model_validate(await get_event_or_404(session, event_id))


@router.patch("/{event_id}", response_model=EventRead)
async def patch_event(
    event_id: UUID,
    payload: EventUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    event = await get_event_or_404(session, event_id)
    event, _ = await update_event(session, event, payload, request.state.request_id)
    return EventRead.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    await soft_delete_event(
        session, await get_event_or_404(session, event_id), request.state.request_id
    )


@router.get("/{event_id}/versions", response_model=list[VersionRead])
async def list_versions(
    event_id: UUID, session: AsyncSession = Depends(get_session)
) -> list[VersionRead]:
    await get_event_or_404(session, event_id)
    versions = await session.scalars(
        select(EventVersion)
        .where(EventVersion.event_id == event_id)
        .order_by(EventVersion.version.desc())
    )
    return [VersionRead.model_validate(item) for item in versions]


@router.get("/{event_id}/changes", response_model=list[ChangeRead])
async def list_event_changes(
    event_id: UUID, session: AsyncSession = Depends(get_session)
) -> list[ChangeRead]:
    await get_event_or_404(session, event_id)
    changes = await session.scalars(
        select(EventChange)
        .where(EventChange.event_id == event_id)
        .order_by(EventChange.created_at.desc())
    )
    return [ChangeRead.model_validate(item) for item in changes]


@router.get("/{event_id}/locks", response_model=list[FieldLockRead])
async def list_locks(
    event_id: UUID, session: AsyncSession = Depends(get_session)
) -> list[FieldLockRead]:
    await get_event_or_404(session, event_id)
    locks = await session.scalars(
        select(EventFieldLock)
        .where(EventFieldLock.event_id == event_id)
        .order_by(EventFieldLock.field_name)
    )
    return [FieldLockRead.model_validate(item) for item in locks]


@router.put("/{event_id}/locks/{field_name}", response_model=FieldLockRead)
async def put_lock(
    event_id: UUID,
    field_name: str,
    payload: FieldLockCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> FieldLockRead:
    event = await get_event_or_404(session, event_id)
    return FieldLockRead.model_validate(
        await lock_field(session, event, field_name, payload.reason, request.state.request_id)
    )


@router.delete("/{event_id}/locks/{field_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lock(
    event_id: UUID,
    field_name: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    await get_event_or_404(session, event_id)
    lock_id = await session.scalar(select(EventFieldLock.id).where(
        EventFieldLock.event_id == event_id, EventFieldLock.field_name == field_name
    ))
    if lock_id is None:
        raise ApiError(404, "lock_not_found", "字段锁不存在")
    await session.execute(delete(EventFieldLock).where(EventFieldLock.id == lock_id))
    session.add(AuditLog(
        actor_id="admin",
        action="field.unlock",
        entity_type="event",
        entity_id=event_id,
        request_id=request.state.request_id,
        before={"field": field_name},
        after=None,
        created_at=utc_now(),
    ))
    await session.commit()
