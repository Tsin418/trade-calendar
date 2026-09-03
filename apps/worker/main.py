import asyncio
import logging
import os
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from trade_calendar.core.config import get_settings
from trade_calendar.core.database import SessionLocal
from trade_calendar.core.logging import configure_logging
from trade_calendar.models.domain import FetchRun, RunStatus, Source, WorkerHeartbeat
from trade_calendar.notifications import deliver_notification, due_notification
from trade_calendar.scheduling import enqueue_scheduled_run, refresh_stale_sources
from trade_calendar.source_registry import adapter_registry, seed_sources
from trade_calendar.sync import SyncRunner, make_run

configure_logging(os.getenv("CALENDAR_LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)
WORKER_NAME = os.getenv("CALENDAR_WORKER_NAME", "scheduler-1")
runner = SyncRunner(SessionLocal)
settings = get_settings()


async def write_heartbeat() -> None:
    async with SessionLocal() as session:
        statement = pg_insert(WorkerHeartbeat).values(
            worker_name=WORKER_NAME,
            heartbeat_at=datetime.now(UTC),
            metadata_json={"pid": os.getpid()},
        ).on_conflict_do_update(
            index_elements=[WorkerHeartbeat.worker_name],
            set_={
                "heartbeat_at": datetime.now(UTC),
                "metadata_json": {"pid": os.getpid()},
            },
        )
        await session.execute(statement)
        await session.commit()
    logger.info({"event": "worker_heartbeat", "worker": WORKER_NAME})


async def process_pending_run() -> None:
    async with SessionLocal() as claim_session:
        run = await claim_session.scalar(
            select(FetchRun)
            .where(FetchRun.status == RunStatus.PENDING)
            .order_by(FetchRun.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if run is None:
            return
        run.status = RunStatus.RUNNING
        source_id = run.source_id
        run_id = run.id
        await claim_session.commit()

    async with SessionLocal() as lock_session:
        acquired = bool(await lock_session.scalar(
            select(func.pg_try_advisory_lock(func.hashtext(str(source_id))))
        ))
        if not acquired:
            async with SessionLocal() as release_session:
                pending = await release_session.get(FetchRun, run_id)
                if pending:
                    pending.status = RunStatus.PENDING
                    await release_session.commit()
            return
        try:
            async with SessionLocal() as source_session:
                run = await source_session.get(FetchRun, run_id)
                source = await source_session.get(Source, source_id)
                adapter = adapter_registry().get(source.key) if source else None
                if run is None or adapter is None:
                    if run:
                        run.status = RunStatus.FAILED
                        run.error_type = "adapter_unavailable"
                        run.error_message = "No adapter is registered for this source"
                        await source_session.commit()
                    return
            result = await runner.execute(run_id, adapter)
            logger.info({
                "event": "sync_completed",
                "run_id": str(result.id),
                "status": result.status.value,
            })
        finally:
            await lock_session.execute(
                select(func.pg_advisory_unlock(func.hashtext(str(source_id))))
            )


async def process_due_notification() -> None:
    if settings.feishu_webhook_url is None:
        return
    async with SessionLocal() as session:
        notification = await due_notification(session)
        if notification is None:
            return
        await deliver_notification(
            session,
            notification,
            settings.feishu_webhook_url.get_secret_value(),
            settings.public_base_url,
        )


async def enqueue_scheduled_source(source_key: str) -> None:
    adapter = adapter_registry().get(source_key)
    if adapter is None:
        return
    async with SessionLocal() as session:
        run, created = await enqueue_scheduled_run(session, source_key, adapter)
    if created and run is not None:
        logger.info({
            "event": "sync_queued",
            "source": source_key,
            "run_id": str(run.id),
        })


async def refresh_source_health() -> None:
    async with SessionLocal() as session:
        changed = await refresh_stale_sources(session)
    if changed:
        logger.info({"event": "source_health_refreshed", "changed": changed})


async def enqueue_never_run_sources() -> None:
    registry = adapter_registry()
    async with SessionLocal() as session:
        sources = list(await session.scalars(
            select(Source).where(Source.enabled.is_(True), Source.key.in_(registry))
        ))
        for source in sources:
            has_run = await session.scalar(
                select(FetchRun.id).where(FetchRun.source_id == source.id).limit(1)
            )
            if has_run is None:
                run = make_run(source, registry[source.key], trigger="initial")
                session.add(run)
        await session.commit()


async def main() -> None:
    async with SessionLocal() as session:
        await seed_sources(session)
        registry = adapter_registry()
        source_schedules = list(await session.execute(
            select(Source.key, Source.schedule).where(
                Source.enabled.is_(True), Source.key.in_(registry)
            )
        ))
    await enqueue_never_run_sources()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        write_heartbeat,
        "interval",
        minutes=1,
        id="worker-heartbeat",
        max_instances=1,
    )
    scheduler.add_job(
        process_pending_run,
        "interval",
        seconds=15,
        id="pending-sync-runs",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        process_due_notification,
        "interval",
        seconds=15,
        id="due-notifications",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        refresh_source_health,
        "interval",
        minutes=15,
        id="source-health-refresh",
        max_instances=1,
        coalesce=True,
    )
    for source_key, schedule in source_schedules:
        scheduler.add_job(
            enqueue_scheduled_source,
            CronTrigger.from_crontab(schedule, timezone="UTC"),
            args=[source_key],
            id=f"source-sync:{source_key}",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
    scheduler.start()
    await write_heartbeat()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
