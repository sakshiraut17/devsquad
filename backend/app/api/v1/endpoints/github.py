from typing import List, Optional
from fastapi import APIRouter, Query, status
from app.schemas.repository import (
    RepositoryResponse,
    IssueResponse,
    FileTreeNode,
    FileContentResponse,
)
from app.services.github_service import github_service

router = APIRouter(prefix="/github", tags=["GitHub"])


@router.get("/repos/{owner}/{repo}", response_model=RepositoryResponse)
async def get_repository(owner: str, repo: str) -> RepositoryResponse:
    """Retrieve GitHub repository information and verify existence."""
    return await github_service.get_repo_info(owner=owner, repo=repo)


@router.get("/repos/{owner}/{repo}/issues", response_model=List[IssueResponse])
async def list_issues(
    owner: str,
    repo: str,
    state: str = Query(default="open", pattern="^(open|closed|all)$"),
) -> List[IssueResponse]:
    """Retrieve issues from a GitHub repository."""
    return await github_service.list_repo_issues(owner=owner, repo=repo, state=state)


@router.get("/repos/{owner}/{repo}/issues/{issue_number}", response_model=IssueResponse)
async def get_issue(owner: str, repo: str, issue_number: int) -> IssueResponse:
    """Retrieve detailed information for a specific issue number."""
    return await github_service.get_issue_detail(owner=owner, repo=repo, issue_number=issue_number)


@router.get("/repos/{owner}/{repo}/tree", response_model=List[FileTreeNode])
async def get_repository_tree(
    owner: str,
    repo: str,
    branch: Optional[str] = Query(default=None),
) -> List[FileTreeNode]:
    """Inspect repository file tree structure."""
    return await github_service.get_repo_tree(owner=owner, repo=repo, branch=branch)


@router.get("/repos/{owner}/{repo}/file", response_model=FileContentResponse)
async def get_file_content(
    owner: str,
    repo: str,
    path: str = Query(..., description="File path relative to repository root"),
    branch: Optional[str] = Query(default=None),
) -> FileContentResponse:
    """Safely fetch file contents from the repository."""
    return await github_service.get_file_content(owner=owner, repo=repo, path=path, branch=branch)
