"""Issue management API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.issue import Issue
from app.db.models.repository import Repository
from app.db.session import get_db
from app.schemas.issue import IssueCreate, IssueResponse

router = APIRouter(prefix="/issues", tags=["Issues"])


@router.get("", response_model=list[IssueResponse])
async def list_issues(
    repository_id: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[Issue]:
    """Retrieve persisted issues with optional filtering and pagination."""
    query = select(Issue)
    if repository_id:
        query = query.where(Issue.repository_id == repository_id)
    if state:
        query = query.where(Issue.state == state)
    query = query.offset(skip).limit(limit).order_by(Issue.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    payload: IssueCreate,
    db: AsyncSession = Depends(get_db),
) -> Issue:
    """Persist an ingested GitHub issue."""
    # Verify repository exists
    repo_result = await db.execute(
        select(Repository).where(Repository.id == payload.repository_id)
    )
    if not repo_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{payload.repository_id}' does not exist.",
        )

    # Check for duplicate issue in this repository
    existing = await db.execute(
        select(Issue).where(
            Issue.repository_id == payload.repository_id,
            Issue.github_issue_number == payload.github_issue_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Issue #{payload.github_issue_number} is already recorded for repository '{payload.repository_id}'.",
        )

    issue = Issue(
        repository_id=payload.repository_id,
        github_issue_number=payload.github_issue_number,
        title=payload.title,
        body=payload.body,
        state=payload.state,
        labels=payload.labels,
        html_url=payload.html_url,
    )
    db.add(issue)
    try:
        await db.commit()
        await db.refresh(issue)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Integrity violation while persisting issue.",
        ) from exc

    return issue


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: str,
    db: AsyncSession = Depends(get_db),
) -> Issue:
    """Retrieve a single issue by its unique identifier."""
    issue = await db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue '{issue_id}' not found.",
        )
    return issue
