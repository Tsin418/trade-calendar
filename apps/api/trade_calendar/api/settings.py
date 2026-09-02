from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.core.database import get_session
from trade_calendar.preferences import load_web_settings, persist_web_settings
from trade_calendar.schemas.settings import WebSettings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=WebSettings)
async def get_web_settings(session: AsyncSession = Depends(get_session)) -> WebSettings:
    return await load_web_settings(session)


@router.put("", response_model=WebSettings)
async def put_web_settings(
    payload: WebSettings,
    session: AsyncSession = Depends(get_session),
) -> WebSettings:
    return await persist_web_settings(session, payload)
