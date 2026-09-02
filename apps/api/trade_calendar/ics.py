from datetime import UTC, datetime, timedelta
from typing import cast

from icalendar import Calendar
from icalendar import Event as ICalEvent

from trade_calendar.models.domain import DatePrecision, Event, EventStatus


def build_calendar(events: list[Event], public_base_url: str) -> bytes:
    calendar = Calendar()
    calendar.add("prodid", "-//Trade Calendar//Private Market Events//ZH-CN")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("method", "PUBLISH")
    calendar.add("x-wr-calname", "交易事件日历")
    calendar.add("x-wr-timezone", "UTC")
    for event in events:
        calendar.add_component(build_ics_event(event, public_base_url))
    return cast(bytes, calendar.to_ical())


def build_ics_event(event: Event, public_base_url: str) -> ICalEvent:
    item = ICalEvent()
    item.add("uid", f"{event.id}@trade-calendar.local")
    item.add("summary", event.title_zh)
    item.add("sequence", event.current_version)
    item.add("dtstamp", _as_utc(event.updated_at))
    item.add("last-modified", _as_utc(event.updated_at))
    item.add("url", f"{public_base_url.rstrip('/')}/events/{event.id}")
    item.add(
        "description",
        "\n".join(filter(None, [
            event.title_original,
            f"机构：{event.institution}",
            f"状态：{event.status.value}",
            f"时间精度：{event.date_precision.value}",
            f"原始时间：{event.original_time_text}" if event.original_time_text else None,
        ])),
    )
    if event.date_precision == DatePrecision.DATE:
        if event.local_date is None:
            raise ValueError("date-only event is missing local_date")
        item.add("dtstart", event.local_date)
        item.add("dtend", event.local_date + timedelta(days=1))
        item.add("x-time-precision", "DATE")
    elif event.starts_at is not None:
        item.add("dtstart", _as_utc(event.starts_at))
        if event.ends_at:
            item.add("dtend", _as_utc(event.ends_at))
        item.add("x-time-precision", event.date_precision.value.upper())
    elif event.local_date is not None:
        item.add("dtstart", event.local_date)
        item.add("dtend", event.local_date + timedelta(days=1))
        item.add("x-time-precision", "UNKNOWN")
    else:
        raise ValueError("ICS event has neither datetime nor local_date")
    if event.original_timezone:
        item.add("x-original-timezone", event.original_timezone)
    if event.status == EventStatus.CANCELLED:
        item.add("status", "CANCELLED")
    else:
        item.add("status", "CONFIRMED" if event.status == EventStatus.CONFIRMED else "TENTATIVE")
    item.add("transp", "TRANSPARENT" if event.status == EventStatus.CANCELLED else "OPAQUE")
    return item


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
