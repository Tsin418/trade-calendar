from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from trade_calendar.models.domain import RunStatus, SourceHealth


class SourceRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: RunStatus
    trigger: str
    started_at: datetime | None
    finished_at: datetime | None
    parsed_count: int
    created_count: int
    updated_count: int
    error_type: str | None
    error_message: str | None

    @field_validator("started_at", "finished_at", mode="before")
    @classmethod
    def restore_utc(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    institution: str
    country_code: str
    official_url: str
    source_type: str
    priority: int
    enabled: bool
    health: SourceHealth
    schedule: str
    stale_after_hours: int
    consecutive_failures: int
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_event_count: int | None
    categories: list[str] = Field(default_factory=list)
    role: str = "primary"
    expected_items: dict[str, int] = Field(default_factory=dict)
    terms: str = ""
    fallback: str = ""
    adapter_available: bool = False
    is_internal: bool = False
    last_run: SourceRunSummary | None = None

    @field_validator("last_success_at", "last_failure_at", mode="before")
    @classmethod
    def restore_utc(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class FetchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    run_key: str
    trigger: str
    status: RunStatus
    adapter_version: str
    started_at: datetime | None
    finished_at: datetime | None
    fetched_count: int
    parsed_count: int
    created_count: int
    updated_count: int
    error_type: str | None
    error_message: str | None

    @field_validator("started_at", "finished_at", mode="before")
    @classmethod
    def restore_utc(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value
