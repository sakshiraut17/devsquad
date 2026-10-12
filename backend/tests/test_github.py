import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from app.services.github_service import github_service
from app.schemas.repository import RepositoryResponse, IssueResponse


@pytest.mark.asyncio
async def test_get_repo_info_endpoint(async_client: AsyncClient):
    """Verify repository info endpoint returns correct structure."""
    mock_repo = RepositoryResponse(
        full_name="octocat/Hello-World",
        default_branch="main",
        is_active=True,
        description="My first repo",
        stars_count=42,
        open_issues_count=3,
    )

    with patch.object(github_service, "get_repo_info", new_callable=AsyncMock) as mock_method:
        mock_method.return_value = mock_repo
        response = await async_client.get("/api/v1/github/repos/octocat/Hello-World")
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "octocat/Hello-World"
        assert data["stars_count"] == 42


@pytest.mark.asyncio
async def test_list_issues_endpoint(async_client: AsyncClient):
    """Verify issues list endpoint returns list of issues."""
    mock_issues = [
        IssueResponse(
            issue_number=1,
            title="Real issue",
            body="Fix this bug",
            state="open",
            author="octocat",
            labels=["bug"],
        )
    ]

    with patch.object(github_service, "list_repo_issues", new_callable=AsyncMock) as mock_method:
        mock_method.return_value = mock_issues
        response = await async_client.get("/api/v1/github/repos/octocat/Hello-World/issues")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["issue_number"] == 1
        assert data[0]["title"] == "Real issue"


@pytest.mark.asyncio
async def test_path_traversal_prohibited(async_client: AsyncClient):
    """Verify path traversal attempts are rejected with HTTP 400."""
    response = await async_client.get(
        "/api/v1/github/repos/octocat/Hello-World/file",
        params={"path": "../../etc/passwd"},
    )
    assert response.status_code == 400
    assert "directory traversal is prohibited" in response.json()["detail"]


@pytest.mark.asyncio
async def test_repo_not_found_endpoint(async_client: AsyncClient):
    """Verify 404 error returned when repository is not found."""
    with patch.object(github_service, "get_repo_info", new_callable=AsyncMock) as mock_method:
        mock_method.side_effect = HTTPException(status_code=404, detail="Repository 'foo/bar' not found on GitHub.")
        response = await async_client.get("/api/v1/github/repos/foo/bar")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
