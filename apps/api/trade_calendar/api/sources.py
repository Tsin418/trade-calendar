from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trade_calendar.core.database import get_session
from trade_calendar.core.errors import ApiError
from trade_calendar.models.domain import FetchRun, Source
from trade_calendar.schemas.sources import FetchRunRead, SourceRead
from trade_calendar.source_registry import adapter_registry, seed_sources
from trade_calendar.sync import make_run

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceRead])
async def list_sources(session: AsyncSession = Depends(get_session)) -> list[SourceRead]:
    if await session.scalar(select(Source.id).limit(1)) is None:
        await seed_sources(session)
    sources = await session.scalars(
        select(Source).order_by(Source.priority.asc(), Source.country_code.asc(), Source.name.asc())
    )
    return [SourceRead.model_validate(source) for source in sources]


@router.get("/sources/{source_id}/runs", response_model=list[FetchRunRead])
async def list_source_runs(
    source_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[FetchRunRead]:
    if await session.get(Source, source_id) is None:
        raise ApiError(404, "source_not_found", "数据源不存在")
    runs = await session.scalars(
        select(FetchRun)
        .where(FetchRun.source_id == source_id)
        .order_by(FetchRun.created_at.desc())
        .limit(limit)
    )
    return [FetchRunRead.model_validate(run) for run in runs]


@router.post(
    "/sources/{source_id}/sync",
    response_model=FetchRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_source(
    source_id: UUID, session: AsyncSession = Depends(get_session)
) -> FetchRunRead:
    source = await session.get(Source, source_id)
    if source is None:
        raise ApiError(404, "source_not_found", "数据源不存在")
    if not source.enabled:
        raise ApiError(409, "source_disabled", "数据源当前已停用")
    adapter = adapter_registry().get(source.key)
    if adapter is None:
        raise ApiError(409, "adapter_unavailable", "该来源的 Adapter 尚未启用")
    run = make_run(source, adapter)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return FetchRunRead.model_validate(run)


@router.post("/sync", response_model=list[FetchRunRead], status_code=status.HTTP_202_ACCEPTED)
async def sync_all(session: AsyncSession = Depends(get_session)) -> list[FetchRunRead]:
    registry = adapter_registry()
    sources = await session.scalars(
        select(Source).where(Source.enabled.is_(True), Source.key.in_(registry))
    )
    runs: list[FetchRun] = []
    timestamp = datetime.now(UTC).isoformat()
    for source in sources:
        run = make_run(source, registry[source.key], trigger="manual-all")
        run.run_key = f"{source.key}:manual-all:{timestamp}"
        session.add(run)
        runs.append(run)
    await session.commit()
    for run in runs:
        await session.refresh(run)
    return [FetchRunRead.model_validate(run) for run in runs]


@router.get("/jobs/{run_id}", response_model=FetchRunRead)
async def get_job(
    run_id: UUID, session: AsyncSession = Depends(get_session)
) -> FetchRunRead:
    run = await session.get(FetchRun, run_id)
    if run is None:
        raise ApiError(404, "job_not_found", "同步任务不存在")
    return FetchRunRead.model_validate(run)

