from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.core.database import get_session
from trade_calendar.models.domain import EventChange
from trade_calendar.schemas.events import ChangeRead

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("", response_model=list[ChangeRead])
async def list_changes(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[ChangeRead]:
    items = await session.scalars(
        select(EventChange).order_by(EventChange.created_at.desc()).limit(limit)
    )
    return [ChangeRead.model_validate(item) for item in items]

