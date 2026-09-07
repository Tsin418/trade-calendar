from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from trade_calendar.languages import display_text
from trade_calendar.models.domain import DatePrecision, EventStatus, Importance


class EventBase(BaseModel):
    title_zh: str = Field(min_length=1, max_length=500)
    title_original: str | None = Field(default=None, max_length=500)
    institution: str = Field(min_length=1, max_length=255)
    country_code: str = Field(min_length=2, max_length=8)
    category: str = Field(min_length=1, max_length=64)
    event_type: str = Field(min_length=1, max_length=64)
    status: EventStatus = EventStatus.CONFIRMED
    importance: Importance = Importance.MEDIUM
    date_precision: DatePrecision
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    local_date: date | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None
    original_timezone: str | None = Field(default=None, max_length=64)
    original_time_text: str | None = Field(default=None, max_length=255)
    reference_period: str | None = Field(default=None, max_length=100)
    market_tags: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    notes: str | None = None
    reminder_enabled: bool = True

    @model_validator(mode="after")
    def validate_time_precision(self) -> "EventBase":
        timed = {DatePrecision.MINUTE, DatePrecision.HOUR, DatePrecision.WINDOW}
        if self.date_precision in timed and self.starts_at is None:
            raise ValueError("精确时间或时间窗口事件必须提供 starts_at")
        if self.date_precision == DatePrecision.DATE:
            if self.local_date is None:
                raise ValueError("仅日期事件必须提供 local_date")
            if self.starts_at is not None:
                raise ValueError("仅日期事件不能伪造 starts_at")
        if self.date_precision == DatePrecision.WINDOW and self.ends_at is None:
            raise ValueError("时间窗口事件必须提供 ends_at")
        if self.starts_at and self.starts_at.tzinfo is None:
            raise ValueError("starts_at 必须包含时区")
        if self.ends_at and self.ends_at.tzinfo is None:
            raise ValueError("ends_at 必须包含时区")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at 必须晚于 starts_at")
        if (self.date_range_start is None) != (self.date_range_end is None):
            raise ValueError("日期范围必须同时提供开始和结束日期")
        if self.date_range_start and self.date_range_end:
            if self.date_range_end < self.date_range_start:
                raise ValueError("日期范围结束日期不能早于开始日期")
            if self.local_date and not (
                self.date_range_start <= self.local_date <= self.date_range_end
            ):
                raise ValueError("事件日期必须位于日期范围内")
        if self.original_timezone:
            try:
                ZoneInfo(self.original_timezone)
            except ZoneInfoNotFoundError as exc:
                raise ValueError("original_timezone 必须是有效 IANA 时区") from exc
        return self

    def normalized_utc(self) -> dict[str, Any]:
        values = self.model_dump()
        for key in ("starts_at", "ends_at"):
            value = values[key]
            if value is not None:
                values[key] = value.astimezone(UTC)
        values["country_code"] = self.country_code.upper()
        values["market_tags"] = sorted(set(tag.upper() for tag in self.market_tags))
        values["tickers"] = sorted(set(ticker.upper() for ticker in self.tickers))
        return values


class EventCreate(EventBase):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=255)


class EventUpdate(BaseModel):
    title_zh: str | None = Field(default=None, min_length=1, max_length=500)
    title_original: str | None = Field(default=None, max_length=500)
    institution: str | None = Field(default=None, min_length=1, max_length=255)
    country_code: str | None = Field(default=None, min_length=2, max_length=8)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    event_type: str | None = Field(default=None, min_length=1, max_length=64)
    status: EventStatus | None = None
    importance: Importance | None = None
    date_precision: DatePrecision | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    local_date: date | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None
    original_timezone: str | None = Field(default=None, max_length=64)
    original_time_text: str | None = Field(default=None, max_length=255)
    reference_period: str | None = Field(default=None, max_length=100)
    market_tags: list[str] | None = None
    tickers: list[str] | None = None
    notes: str | None = None
    reminder_enabled: bool | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    canonical_key: str
    title_zh: str
    title_original: str | None
    normalized_title: str
    institution: str
    country_code: str
    category: str
    event_type: str
    status: EventStatus
    importance: Importance
    date_precision: DatePrecision
    starts_at: datetime | None
    ends_at: datetime | None
    local_date: date | None
    date_range_start: date | None
    date_range_end: date | None
    original_timezone: str | None
    original_time_text: str | None
    reference_period: str | None
    market_tags: list[str]
    tickers: list[str]
    notes: str | None
    reminder_enabled: bool
    is_manual: bool
    is_deleted: bool
    current_version: int
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    translations: dict[str, str] = Field(default_factory=dict, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_title(self) -> str:
        original = (self.title_original or "").strip()
        return display_text(
            original or self.title_zh, self.translations, self.title_zh,
            placeholder="标题翻译中",
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_institution(self) -> str:
        return display_text(self.institution, self.translations, placeholder="机构名称翻译中")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_original_time_text(self) -> str | None:
        if not self.original_time_text:
            return None
        return display_text(self.original_time_text, self.translations)

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def restore_utc_for_naive_test_databases(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class EventList(BaseModel):
    items: list[EventRead]
    total: int
    limit: int
    offset: int


class EventSourceRead(BaseModel):
    source_id: UUID
    source_key: str
    source_name: str
    institution: str
    official_url: str
    source_event_id: str | None
    source_title: str | None
    is_primary: bool
    last_verified_at: datetime | None
    translations: dict[str, str] = Field(default_factory=dict, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_title(self) -> str:
        return display_text(self.source_title or self.institution, self.translations)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_source_name(self) -> str:
        return display_text(self.source_name, self.translations)

    @field_validator("last_verified_at", mode="before")
    @classmethod
    def restore_verified_at_utc(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    version: int
    snapshot: dict[str, Any]
    actor_type: str
    actor_id: str | None
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def restore_created_at_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class ChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    from_version: int | None
    to_version: int
    change_type: str
    changed_fields: dict[str, Any]
    created_at: datetime
    translations: dict[str, str] = Field(default_factory=dict, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_changed_fields(self) -> dict[str, Any]:
        return {
            field: {
                side: display_text(value, self.translations) if isinstance(value, str) else value
                for side, value in values.items()
            }
            for field, values in self.changed_fields.items()
        }

    @field_validator("created_at", mode="before")
    @classmethod
    def restore_created_at_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class FieldLockCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class FieldLockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    field_name: str
    locked_by: str
    reason: str | None
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def restore_created_at_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value
