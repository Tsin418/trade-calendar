from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from trade_calendar.models.domain import DatePrecision, EventStatus, Importance


class SourceKind(StrEnum):
    API = "api"
    RSS = "rss"
    ICS = "ics"
    HTML = "html"
    PDF = "pdf"


class RawPayload(BaseModel):
    source_key: str
    url: str
    content: bytes
    content_type: str
    http_status: int = 200
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    headers: dict[str, str] = Field(default_factory=dict)


class SourceEvent(BaseModel):
    source_event_id: str
    title: str
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    local_date: date | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None
    original_timezone: str | None = None
    original_time_text: str | None = None
    reference_period: str | None = None
    status_text: str | None = None
    url: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class NormalizedEvent(BaseModel):
    source_event_id: str
    title_zh: str
    title_original: str
    institution: str
    country_code: str
    category: str
    event_type: str
    status: EventStatus
    importance: Importance
    date_precision: DatePrecision
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    local_date: date | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None
    original_timezone: str | None = None
    original_time_text: str | None = None
    reference_period: str | None = None
    market_tags: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    source_url: str
    raw: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_time(self) -> "NormalizedEvent":
        if self.date_precision == DatePrecision.DATE:
            if self.local_date is None or self.starts_at is not None:
                raise ValueError("date precision requires local_date and forbids starts_at")
        elif self.date_precision in {
            DatePrecision.MINUTE,
            DatePrecision.HOUR,
            DatePrecision.WINDOW,
        }:
            if self.starts_at is None or self.starts_at.tzinfo is None:
                raise ValueError("timed event requires timezone-aware starts_at")
        if self.date_precision == DatePrecision.WINDOW and self.ends_at is None:
            raise ValueError("window event requires ends_at")
        if (self.date_range_start is None) != (self.date_range_end is None):
            raise ValueError("date range requires both start and end")
        if self.date_range_start and self.date_range_end:
            if self.date_range_end < self.date_range_start:
                raise ValueError("date range end must not precede start")
            if self.local_date and not (
                self.date_range_start <= self.local_date <= self.date_range_end
            ):
                raise ValueError("local_date must fall within the date range")
        return self


class AdapterHealth(BaseModel):
    healthy: bool
    event_count: int
    completeness: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
