from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.core.config import get_settings
from trade_calendar.core.database import get_session
from trade_calendar.core.errors import ApiError
from trade_calendar.models.domain import Event, Notification, NotificationStatus
from trade_calendar.notifications import deliver_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/test/{event_id}")
async def test_notification(
    event_id: UUID, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    settings = get_settings()
    if settings.feishu_webhook_url is None:
        raise ApiError(409, "feishu_not_configured", "尚未配置飞书 Webhook")
    event = await session.get(Event, event_id)
    if event is None or event.is_deleted:
        raise ApiError(404, "event_not_found", "事件不存在")
    notification = Notification(
        event_id=event.id,
        channel="feishu",
        alert_type="manual_test",
        scheduled_at=event.starts_at or event.updated_at,
        event_version=event.current_version,
        status=NotificationStatus.PENDING,
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    sent = await deliver_notification(
        session,
        notification,
        settings.feishu_webhook_url.get_secret_value(),
        settings.public_base_url,
    )
    return {"status": "sent" if sent else "failed", "notification_id": str(notification.id)}

