"""Repository management API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_authorized_repository
from app.db.models.issue import Issue
from app.db.models.repository import Repository
from app.db.session import get_db
from app.schemas.issue import IssueResponse
from app.schemas.repository import RepositoryCreate, RepositoryResponse

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
) -> list[Repository]:
    """Retrieve persisted repositories with pagination."""
    query = select(Repository)
    if active_only:
        query = query.where(Repository.is_active == True)
    query = query.offset(skip).limit(limit).order_by(Repository.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    payload: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """Register a new GitHub repository in DevSquad."""
    # Check for existing repository
    existing = await db.execute(
        select(Repository).where(
            (Repository.github_repository_id == payload.github_repository_id)
            | (Repository.full_name == payload.full_name)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository with name '{payload.full_name}' or GitHub ID '{payload.github_repository_id}' already registered.",
        )

    repo = Repository(
        owner_id=payload.owner_id,
        github_repository_id=payload.github_repository_id,
        full_name=payload.full_name,
        default_branch=payload.default_branch,
        description=payload.description,
        is_active=True,
    )
    db.add(repo)
    try:
        await db.commit()
        await db.refresh(repo)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Integrity conflict while saving repository.",
        ) from exc

    return repo


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: str,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """Retrieve a single registered repository."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found.",
        )
    return repo


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a registered repository and cascade delete its associated issues, runs, and artifacts."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found.",
        )
    await db.delete(repo)
    await db.commit()
    return None


@router.get("/{repository_id}/github-issues", response_model=list[dict])
async def list_repository_github_issues(
    repository_id: str,
    state: str = Query(default="open"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    repo: Repository = Depends(get_authorized_repository),
) -> list[dict]:
    """Retrieve real issues directly from GitHub for an authorized repository."""
    from app.core.config import settings
    from app.services.github_service import (
        GitHubAPIError,
        GitHubAuthError,
        GitHubRateLimitError,
        GitHubResourceNotFoundError,
        GitHubService,
    )

    if "/" not in repo.full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository '{repo.full_name}' is not in valid owner/repo format.",
        )
    owner, name = repo.full_name.split("/", 1)

    has_token = bool(settings.github_token.get_secret_value())
    if not has_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub API credentials are not configured (DEVSQUAD_GITHUB_TOKEN missing). Remote issue retrieval unavailable.",
        )

    try:
        async with GitHubService(token=settings.github_token.get_secret_value()) as gh:
            issues = await gh.list_issues(owner, name, state=state, page=page, per_page=per_page)
            return [issue.model_dump() for issue in issues]
    except GitHubAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"GitHub authentication error: {str(exc)}",
        ) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"GitHub API rate limit exceeded: {str(exc)}",
        ) from exc
    except GitHubResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repo.full_name}' not found on GitHub.",
        ) from exc
    except GitHubAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub API request failed: {str(exc)}",
        ) from exc


@router.get("/{repository_id}/github-issues/{issue_number}", response_model=dict)
async def get_repository_github_issue(
    repository_id: str,
    issue_number: int,
    repo: Repository = Depends(get_authorized_repository),
) -> dict:
    """Retrieve details for a specific issue from GitHub along with target branch and commit SHA."""
    from app.core.config import settings
    from app.services.github_service import (
        GitHubAPIError,
        GitHubAuthError,
        GitHubRateLimitError,
        GitHubResourceNotFoundError,
        GitHubService,
    )

    if "/" not in repo.full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository '{repo.full_name}' is not in valid owner/repo format.",
        )
    owner, name = repo.full_name.split("/", 1)

    has_token = bool(settings.github_token.get_secret_value())
    if not has_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub API credentials are not configured (DEVSQUAD_GITHUB_TOKEN missing). Remote issue retrieval unavailable.",
        )

    try:
        async with GitHubService(token=settings.github_token.get_secret_value()) as gh:
            gh_issue = await gh.get_issue(owner, name, issue_number)
            target_branch = repo.default_branch or "main"
            base_commit_sha = "unknown"
            try:
                branch_meta = await gh.get_branch(owner, name, target_branch)
                base_commit_sha = branch_meta.commit_sha
            except Exception:
                pass

            return {
                "issue": gh_issue.model_dump(),
                "target_branch": target_branch,
                "base_commit_sha": base_commit_sha,
            }
    except GitHubAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"GitHub authentication error: {str(exc)}",
        ) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"GitHub API rate limit exceeded: {str(exc)}",
        ) from exc
    except GitHubResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue #{issue_number} or repository '{repo.full_name}' not found on GitHub.",
        ) from exc
    except GitHubAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub API request failed: {str(exc)}",
        ) from exc


@router.post("/{repository_id}/sync-issue/{issue_number}", response_model=IssueResponse)
async def sync_repository_github_issue(
    repository_id: str,
    issue_number: int,
    repo: Repository = Depends(get_authorized_repository),
    db: AsyncSession = Depends(get_db),
) -> Issue:
    """Fetch an issue from GitHub and persist or update it in the DevSquad database."""
    from app.core.config import settings
    from app.db.models.issue import Issue
    from app.services.github_service import (
        GitHubAPIError,
        GitHubAuthError,
        GitHubRateLimitError,
        GitHubResourceNotFoundError,
        GitHubService,
    )

    if "/" not in repo.full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository '{repo.full_name}' is not in valid owner/repo format.",
        )
    owner, name = repo.full_name.split("/", 1)

    has_token = bool(settings.github_token.get_secret_value())
    if not has_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub API credentials are not configured (DEVSQUAD_GITHUB_TOKEN missing). Remote issue sync unavailable.",
        )

    try:
        async with GitHubService(token=settings.github_token.get_secret_value()) as gh:
            gh_issue = await gh.get_issue(owner, name, issue_number)
    except GitHubAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"GitHub authentication error: {str(exc)}",
        ) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"GitHub API rate limit exceeded: {str(exc)}",
        ) from exc
    except GitHubResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue #{issue_number} not found on GitHub repository '{repo.full_name}'.",
        ) from exc
    except GitHubAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub API request failed: {str(exc)}",
        ) from exc

    # Check for existing issue in database
    existing_query = select(Issue).where(
        Issue.repository_id == repo.id,
        Issue.github_issue_number == issue_number,
    )
    res = await db.execute(existing_query)
    issue = res.scalar_one_or_none()

    if issue:
        issue.title = gh_issue.title
        issue.body = gh_issue.body
        issue.state = gh_issue.state
        issue.labels = gh_issue.labels
        issue.html_url = gh_issue.html_url
    else:
        issue = Issue(
            repository_id=repo.id,
            github_issue_number=gh_issue.number,
            title=gh_issue.title,
            body=gh_issue.body,
            state=gh_issue.state,
            labels=gh_issue.labels,
            html_url=gh_issue.html_url,
        )
        db.add(issue)

    await db.commit()
    await db.refresh(issue)
    return issue

