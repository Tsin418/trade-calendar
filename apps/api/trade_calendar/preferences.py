from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.models.domain import SystemSetting
from trade_calendar.schemas.settings import WebSettings

WEB_SETTINGS_KEY = "web_preferences"


async def load_web_settings(session: AsyncSession) -> WebSettings:
    setting = await session.get(SystemSetting, WEB_SETTINGS_KEY)
    if setting is None:
        return WebSettings()
    return WebSettings.model_validate(setting.value_json)


async def persist_web_settings(session: AsyncSession, payload: WebSettings) -> WebSettings:
    setting = await session.get(SystemSetting, WEB_SETTINGS_KEY)
    values = payload.model_dump(mode="json")
    if setting is None:
        session.add(SystemSetting(key=WEB_SETTINGS_KEY, value_json=values))
    else:
        setting.value_json = values
    await session.commit()
    return payload
