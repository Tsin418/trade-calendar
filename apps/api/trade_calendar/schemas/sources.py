from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from trade_calendar.models.domain import RunStatus, SourceHealth


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
    consecutive_failures: int
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_event_count: int | None


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

