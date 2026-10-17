"""System Overview and Dashboard Metrics API."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.issue import Issue
from app.db.models.repository import Repository
from app.db.models.run import Run, RunStatus
from app.db.session import get_db

router = APIRouter(prefix="/overview", tags=["Overview"])


class OverviewStatsResponse(BaseModel):
    """Aggregate counts for dashboard overview cards."""
    repositories_count: int
    open_issues_count: int
    total_runs_count: int
    active_runs_count: int
    awaiting_approval_count: int
    failed_runs_count: int
    completed_runs_count: int


@router.get("/stats", response_model=OverviewStatsResponse)
async def get_overview_stats(db: AsyncSession = Depends(get_db)) -> OverviewStatsResponse:
    """Aggregate high-level system and workflow counts directly from database."""
    repos_cnt = (
        await db.execute(select(func.count(Repository.id)).where(Repository.is_active == True))
    ).scalar() or 0
    issues_cnt = (
        await db.execute(select(func.count(Issue.id)).where(Issue.state == "open"))
    ).scalar() or 0
    total_runs = (await db.execute(select(func.count(Run.id)))).scalar() or 0
    active_runs = (
        await db.execute(
            select(func.count(Run.id)).where(
                Run.status.in_([
                    RunStatus.INGESTING.value,
                    RunStatus.PLANNING.value,
                    RunStatus.CODING.value,
                    RunStatus.TESTING.value,
                    RunStatus.REVIEWING.value,
                    RunStatus.CREATING_PR.value,
                ])
            )
        )
    ).scalar() or 0
    awaiting_approval = (
        await db.execute(
            select(func.count(Run.id)).where(Run.status == RunStatus.AWAITING_APPROVAL.value)
        )
    ).scalar() or 0
    failed_runs = (
        await db.execute(
            select(func.count(Run.id)).where(
                Run.status.in_([RunStatus.FAILED.value, RunStatus.CANCELLED.value])
            )
        )
    ).scalar() or 0
    completed_runs = (
        await db.execute(
            select(func.count(Run.id)).where(
                Run.status.in_([RunStatus.COMPLETED.value, RunStatus.APPROVED.value])
            )
        )
    ).scalar() or 0

    return OverviewStatsResponse(
        repositories_count=repos_cnt,
        open_issues_count=issues_cnt,
        total_runs_count=total_runs,
        active_runs_count=active_runs,
        awaiting_approval_count=awaiting_approval,
        failed_runs_count=failed_runs,
        completed_runs_count=completed_runs,
    )
