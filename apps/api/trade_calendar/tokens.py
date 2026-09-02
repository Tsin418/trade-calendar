import hashlib
import hmac
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.core.config import Settings, get_settings
from trade_calendar.models.domain import SystemSetting

ICS_TOKEN_KEY = "ics_token"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def ensure_ics_token(
    session: AsyncSession, settings: Settings | None = None
) -> SystemSetting:
    setting = await session.get(SystemSetting, ICS_TOKEN_KEY)
    if setting is not None:
        return setting
    settings = settings or get_settings()
    setting = SystemSetting(
        key=ICS_TOKEN_KEY,
        value_json={"sha256": token_hash(settings.ics_token.get_secret_value())},
    )
    session.add(setting)
    await session.commit()
    await session.refresh(setting)
    return setting


async def validate_ics_token(session: AsyncSession, token: str) -> bool:
    setting = await ensure_ics_token(session)
    expected = str(setting.value_json.get("sha256", ""))
    return hmac.compare_digest(expected, token_hash(token))


async def rotate_ics_token(session: AsyncSession) -> str:
    token = secrets.token_urlsafe(32)
    setting = await ensure_ics_token(session)
    setting.value_json = {"sha256": token_hash(token)}
    await session.commit()
    return token

