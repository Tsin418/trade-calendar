from httpx import AsyncClient
from icalendar import Calendar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from trade_calendar.models.domain import Notification, NotificationStatus
from trade_calendar.schemas.events import EventCreate
from trade_calendar.services import create_event


async def test_critical_notification_schedule_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
    minute_event_payload: dict[str, object],
) -> None:
    async with session_factory() as session:
        event, _ = await create_event(
            session, EventCreate.model_validate(minute_event_payload), "create"
        )
        notifications = list(await session.scalars(
            select(Notification).where(Notification.event_id == event.id)
        ))
        assert [item.alert_type for item in notifications] == [
            "before_120m",
            "before_60m",
            "before_15m",
        ]
        assert all(item.event_version == 1 for item in notifications)

        await create_event(
            session, EventCreate.model_validate(minute_event_payload), "repeat"
        )
        count = len(list(await session.scalars(
            select(Notification).where(Notification.event_id == event.id)
        )))
        assert count == 3


async def test_date_only_event_has_no_minute_notifications(client: AsyncClient) -> None:
    response = await client.post("/api/v1/events", json={
        "title_zh": "时间待定事件",
        "institution": "Official",
        "country_code": "JP",
        "category": "corporate",
        "event_type": "earnings_release",
        "status": "tba",
        "importance": "critical",
        "date_precision": "date",
        "local_date": "2026-09-20",
        "original_timezone": "Asia/Tokyo",
    })
    assert response.status_code == 201
    event_id = response.json()["id"]
    preview = await client.get(f"/api/v1/events/{event_id}/calendar-preview")
    assert preview.status_code == 200
    calendar = Calendar.from_ical(preview.content)
    component = next(iter(calendar.walk("VEVENT")))
    assert component.decoded("DTSTART").isoformat() == "2026-09-20"
    assert component.get("X-TIME-PRECISION") == "DATE"


async def test_ics_uid_stays_stable_after_reschedule_and_cancellation(
    client: AsyncClient, minute_event_payload: dict[str, object]
) -> None:
    created = await client.post("/api/v1/events", json=minute_event_payload)
    event_id = created.json()["id"]
    first = Calendar.from_ical(
        (await client.get(f"/api/v1/events/{event_id}/calendar-preview")).content
    )
    first_event = next(iter(first.walk("VEVENT")))

    await client.patch(f"/api/v1/events/{event_id}", json={
        "starts_at": "2026-09-17T14:00:00-04:00",
        "status": "rescheduled",
    })
    second = Calendar.from_ical(
        (await client.get(f"/api/v1/events/{event_id}/calendar-preview")).content
    )
    second_event = next(iter(second.walk("VEVENT")))
    assert str(first_event["UID"]) == str(second_event["UID"])
    assert int(second_event["SEQUENCE"]) == 2

    await client.patch(f"/api/v1/events/{event_id}", json={"status": "cancelled"})
    cancelled = Calendar.from_ical(
        (await client.get(f"/api/v1/events/{event_id}/calendar-preview")).content
    )
    cancelled_event = next(iter(cancelled.walk("VEVENT")))
    assert str(cancelled_event["STATUS"]) == "CANCELLED"


async def test_token_rotation_invalidates_old_feed(
    client: AsyncClient, minute_event_payload: dict[str, object]
) -> None:
    await client.post("/api/v1/events", json=minute_event_payload)
    old = await client.get("/calendar/development-ics-token.ics")
    assert old.status_code == 200
    assert old.headers["content-type"].startswith("text/calendar")

    rotated = await client.post("/api/v1/ics-token/rotate")
    assert rotated.status_code == 201
    token = rotated.json()["token"]
    assert (await client.get("/calendar/development-ics-token.ics")).status_code == 404
    assert (await client.get(f"/calendar/{token}.ics")).status_code == 200


async def test_cancelled_event_cancels_old_notifications(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    minute_event_payload: dict[str, object],
) -> None:
    created = await client.post("/api/v1/events", json=minute_event_payload)
    event_id = created.json()["id"]
    await client.patch(f"/api/v1/events/{event_id}", json={"status": "cancelled"})
    async with session_factory() as session:
        notifications = list(await session.scalars(select(Notification)))
        assert len(notifications) == 3
        assert all(item.status == NotificationStatus.CANCELLED for item in notifications)
