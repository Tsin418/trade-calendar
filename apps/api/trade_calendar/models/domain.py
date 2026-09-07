from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trade_calendar.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DatePrecision(StrEnum):
    MINUTE = "minute"
    HOUR = "hour"
    DATE = "date"
    WINDOW = "window"
    UNKNOWN = "unknown"


class EventStatus(StrEnum):
    CONFIRMED = "confirmed"
    PROVISIONAL = "provisional"
    TBA = "tba"
    EXPECTED = "expected"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    IGNORED = "ignored"


class Importance(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceHealth(StrEnum):
    HEALTHY = "healthy"
    STALE = "stale"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    IGNORED = "ignored"
    MERGED = "merged"


def value_enum(enum_class: type[StrEnum]) -> Enum:
    return Enum(
        enum_class,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
    )


class Event(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "(date_precision IN ('minute','hour','window') AND starts_at IS NOT NULL) "
            "OR (date_precision = 'date' AND local_date IS NOT NULL AND starts_at IS NULL) "
            "OR (date_precision = 'unknown')",
            name="valid_time_precision",
        ),
        CheckConstraint(
            "date_precision != 'window' OR ends_at IS NOT NULL",
            name="window_has_end",
        ),
        Index("ix_events_time_range", "starts_at", "ends_at"),
        Index("ix_events_date_range", "date_range_start", "date_range_end"),
        Index("ix_events_local_date_importance", "local_date", "importance"),
        Index("ix_events_country_category", "country_code", "category"),
    )

    canonical_key: Mapped[str] = mapped_column(String(255), unique=True)
    title_zh: Mapped[str] = mapped_column(String(500))
    title_original: Mapped[str | None] = mapped_column(String(500))
    normalized_title: Mapped[str] = mapped_column(String(500), index=True)
    institution: Mapped[str] = mapped_column(String(255))
    country_code: Mapped[str] = mapped_column(String(8), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[EventStatus] = mapped_column(
        value_enum(EventStatus), default=EventStatus.CONFIRMED, index=True
    )
    importance: Mapped[Importance] = mapped_column(
        value_enum(Importance), default=Importance.MEDIUM, index=True
    )
    date_precision: Mapped[DatePrecision] = mapped_column(
        value_enum(DatePrecision)
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    local_date: Mapped[date | None] = mapped_column(Date, index=True)
    date_range_start: Mapped[date | None] = mapped_column(Date)
    date_range_end: Mapped[date | None] = mapped_column(Date)
    original_timezone: Mapped[str | None] = mapped_column(String(64))
    original_time_text: Mapped[str | None] = mapped_column(String(255))
    reference_period: Mapped[str | None] = mapped_column(String(100))
    market_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    tickers: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    versions: Mapped[list["EventVersion"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    changes: Mapped[list["EventChange"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    locks: Mapped[list["EventFieldLock"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    key: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    institution: Mapped[str] = mapped_column(String(255))
    country_code: Mapped[str] = mapped_column(String(8), index=True)
    official_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(32))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    health: Mapped[SourceHealth] = mapped_column(
        value_enum(SourceHealth), default=SourceHealth.STALE, index=True
    )
    schedule: Mapped[str] = mapped_column(String(100))
    stale_after_hours: Mapped[int] = mapped_column(Integer, default=72)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_event_count: Mapped[int | None] = mapped_column(Integer)


class FetchRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fetch_runs"
    __table_args__ = (Index("ix_fetch_runs_source_started", "source_id", "started_at"),)

    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    run_key: Mapped[str] = mapped_column(String(255), unique=True)
    trigger: Mapped[str] = mapped_column(String(32), default="scheduled")
    status: Mapped[RunStatus] = mapped_column(value_enum(RunStatus), index=True)
    adapter_version: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    parsed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)


class RawSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "raw_snapshots"
    __table_args__ = (UniqueConstraint("source_id", "content_hash"),)

    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    fetch_run_id: Mapped[UUID] = mapped_column(ForeignKey("fetch_runs.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    content_type: Mapped[str] = mapped_column(String(100))
    body: Mapped[bytes] = mapped_column(LargeBinary)
    http_status: Mapped[int] = mapped_column(Integer)
    adapter_version: Mapped[str] = mapped_column(String(50))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SourceObservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_observations"
    __table_args__ = (
        UniqueConstraint("source_id", "source_event_id"),
        Index("ix_observations_event_date", "event_type", "local_date"),
    )

    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    fetch_run_id: Mapped[UUID] = mapped_column(ForeignKey("fetch_runs.id", ondelete="CASCADE"))
    snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("raw_snapshots.id", ondelete="CASCADE"))
    event_id: Mapped[UUID | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"))
    source_event_id: Mapped[str] = mapped_column(String(255))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500))
    institution: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(64))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    local_date: Mapped[date | None] = mapped_column(Date)
    date_range_start: Mapped[date | None] = mapped_column(Date)
    date_range_end: Mapped[date | None] = mapped_column(Date)
    original_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    match_confidence: Mapped[float | None] = mapped_column(Float)
    match_reason: Mapped[str | None] = mapped_column(Text)


class EventSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_sources"
    __table_args__ = (
        UniqueConstraint("event_id", "source_id", name="uq_event_sources_event_source"),
    )

    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    observation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_observations.id", ondelete="SET NULL")
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EventVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "event_versions"
    __table_args__ = (UniqueConstraint("event_id", "version"),)

    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    actor_type: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event: Mapped[Event] = relationship(back_populates="versions")


class EventChange(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "event_changes"
    __table_args__ = (Index("ix_event_changes_created", "created_at"),)

    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    from_version: Mapped[int | None] = mapped_column(Integer)
    to_version: Mapped[int] = mapped_column(Integer)
    change_type: Mapped[str] = mapped_column(String(64), index=True)
    changed_fields: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event: Mapped[Event] = relationship(back_populates="changes")


class EventFieldLock(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_field_locks"
    __table_args__ = (UniqueConstraint("event_id", "field_name"),)

    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    field_name: Mapped[str] = mapped_column(String(100))
    locked_by: Mapped[str] = mapped_column(String(255), default="admin")
    reason: Mapped[str | None] = mapped_column(Text)
    event: Mapped[Event] = relationship(back_populates="locks")


class AlertRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alert_rules"

    name: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    channel: Mapped[str] = mapped_column(String(32), default="feishu")
    rule_type: Mapped[str] = mapped_column(String(64))
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    lead_times_minutes: Mapped[list[int]] = mapped_column(JSON, default=list)


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "channel", "event_id", "alert_type", "scheduled_at", "event_version",
            name="uq_notification_delivery",
        ),
        Index("ix_notifications_due", "status", "scheduled_at"),
    )

    event_id: Mapped[UUID | None] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    alert_rule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="SET NULL")
    )
    channel: Mapped[str] = mapped_column(String(32))
    alert_type: Mapped[str] = mapped_column(String(64))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[NotificationStatus] = mapped_column(
        value_enum(NotificationStatus), default=NotificationStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class ReviewQueueItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_queue"
    __table_args__ = (Index("ix_review_status_created", "status", "created_at"),)

    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_observations.id", ondelete="CASCADE")
    )
    candidate_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL")
    )
    status: Mapped[ReviewStatus] = mapped_column(
        value_enum(ReviewStatus), default=ReviewStatus.PENDING
    )
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    resolution: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_entity_created", "entity_type", "entity_id", "created_at"),)

    actor_id: Mapped[str] = mapped_column(String(255), default="admin")
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[UUID | None]
    request_id: Mapped[str | None] = mapped_column(String(100))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class TextTranslation(TimestampMixin, Base):
    __tablename__ = "text_translations"

    text_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_text: Mapped[str] = mapped_column(Text)
    target_language: Mapped[str] = mapped_column(String(16), default="zh-CN")
    translated_text: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(100), default="agnes-2.5-flash")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(100))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
