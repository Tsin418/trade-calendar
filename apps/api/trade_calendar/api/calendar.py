from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.core.config import get_settings
from trade_calendar.core.database import get_session
from trade_calendar.core.errors import ApiError
from trade_calendar.ics import build_calendar
from trade_calendar.models.domain import Event
from trade_calendar.tokens import rotate_ics_token, validate_ics_token

router = APIRouter(tags=["calendar"])


@router.get("/calendar/{token}.ics", include_in_schema=False)
async def private_calendar(
    token: str, session: AsyncSession = Depends(get_session)
) -> Response:
    if not await validate_ics_token(session, token):
        raise ApiError(404, "calendar_not_found", "订阅地址无效")
    now = datetime.now(UTC)
    events = list(await session.scalars(
        select(Event)
        .where(
            Event.is_deleted.is_(False),
            or_(
                Event.starts_at >= now - timedelta(days=30),
                Event.local_date >= (now - timedelta(days=30)).date(),
            ),
        )
        .order_by(Event.starts_at.asc(), Event.local_date.asc())
    ))
    content = build_calendar(events, get_settings().public_base_url)
    return Response(
        content=content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": "inline; filename=trade-calendar.ics",
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/api/v1/ics-token/rotate", status_code=status.HTTP_201_CREATED)
async def rotate_calendar_token(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    token = await rotate_ics_token(session)
    base = get_settings().public_base_url.rstrip("/")
    return {"token": token, "url": f"{base}/calendar/{token}.ics"}


@router.get("/api/v1/events/{event_id}/calendar-preview")
async def calendar_preview(
    event_id: UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    event = await session.get(Event, event_id)
    if event is None or event.is_deleted:
        raise ApiError(404, "event_not_found", "事件不存在")
    return Response(
        content=build_calendar([event], get_settings().public_base_url),
        media_type="text/calendar; charset=utf-8",
    )

