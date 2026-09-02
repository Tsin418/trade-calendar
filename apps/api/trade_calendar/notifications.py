from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.models.domain import (
    DatePrecision,
    Event,
    EventStatus,
    Importance,
    Notification,
    NotificationStatus,
)
from trade_calendar.preferences import load_web_settings

DEFAULT_LEADS: dict[Importance, list[int]] = {
    Importance.CRITICAL: [120, 60, 15],
    Importance.HIGH: [60, 15],
    Importance.MEDIUM: [30],
    Importance.LOW: [],
}
RETRY_MINUTES = [1, 5, 15]


async def ensure_event_notifications(
    session: AsyncSession, event: Event, now: datetime | None = None
) -> int:
    now = now or datetime.now(UTC)
    existing = list(await session.scalars(select(Notification).where(
        Notification.event_id == event.id,
        Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.FAILED]),
    )))
    for notification in existing:
        if notification.event_version != event.current_version:
            notification.status = NotificationStatus.CANCELLED
    if (
        not event.reminder_enabled
        or event.status in {EventStatus.CANCELLED, EventStatus.IGNORED}
        or event.date_precision in {DatePrecision.DATE, DatePrecision.UNKNOWN}
        or event.starts_at is None
    ):
        return 0
    starts_at = _as_utc(event.starts_at)
    created = 0
    preferences = await load_web_settings(session)
    leads = DEFAULT_LEADS[event.importance]
    if event.importance == Importance.CRITICAL:
        leads = preferences.critical_lead_minutes
    elif event.importance == Importance.HIGH:
        leads = preferences.high_lead_minutes
    for minutes in leads:
        scheduled_at = starts_at - timedelta(minutes=minutes)
        if scheduled_at <= now:
            continue
        duplicate = await session.scalar(select(Notification.id).where(
            Notification.channel == "feishu",
            Notification.event_id == event.id,
            Notification.alert_type == f"before_{minutes}m",
            Notification.scheduled_at == scheduled_at,
            Notification.event_version == event.current_version,
        ))
        if duplicate:
            continue
        session.add(Notification(
            event_id=event.id,
            channel="feishu",
            alert_type=f"before_{minutes}m",
            scheduled_at=scheduled_at,
            event_version=event.current_version,
            status=NotificationStatus.PENDING,
            next_attempt_at=scheduled_at,
        ))
        created += 1
    return created


def build_feishu_message(event: Event, alert_type: str, public_base_url: str) -> dict[str, Any]:
    start = _as_utc(event.starts_at).isoformat() if event.starts_at else "时间待定"
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": "red" if event.importance == Importance.CRITICAL else "orange",
                "title": {"tag": "plain_text", "content": f"事件提醒 · {event.title_zh}"},
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": (
                    f"**机构**：{event.institution}\n"
                    f"**时间（UTC）**：{start}\n"
                    f"**原始时间**：{event.original_time_text or '未提供'}\n"
                    f"**重要性 / 状态**：{event.importance.value} / {event.status.value}\n"
                    f"**影响市场**：{', '.join(event.market_tags)}\n"
                    f"**提醒节点**：{alert_type}\n"
                    f"[查看事件]({public_base_url.rstrip('/')}/events/{event.id})"
                )}},
            ],
        },
    }


async def deliver_notification(
    session: AsyncSession,
    notification: Notification,
    webhook_url: str,
    public_base_url: str,
) -> bool:
    event = await session.get(Event, notification.event_id) if notification.event_id else None
    if event is None:
        notification.status = NotificationStatus.CANCELLED
        await session.commit()
        return False
    notification.status = NotificationStatus.SENDING
    await session.commit()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                webhook_url,
                json=build_feishu_message(event, notification.alert_type, public_base_url),
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        notification.attempts += 1
        notification.last_error = str(exc)[:1000]
        if notification.attempts >= len(RETRY_MINUTES):
            notification.status = NotificationStatus.FAILED
            notification.next_attempt_at = None
        else:
            notification.status = NotificationStatus.FAILED
            notification.next_attempt_at = datetime.now(UTC) + timedelta(
                minutes=RETRY_MINUTES[notification.attempts]
            )
        await session.commit()
        return False
    notification.status = NotificationStatus.SENT
    notification.sent_at = datetime.now(UTC)
    notification.last_error = None
    await session.commit()
    return True


async def due_notification(
    session: AsyncSession, now: datetime | None = None
) -> Notification | None:
    now = now or datetime.now(UTC)
    result = await session.scalar(
        select(Notification)
        .where(
            Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.FAILED]),
            or_(Notification.next_attempt_at.is_(None), Notification.next_attempt_at <= now),
            Notification.scheduled_at <= now,
        )
        .order_by(Notification.scheduled_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    return result


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
