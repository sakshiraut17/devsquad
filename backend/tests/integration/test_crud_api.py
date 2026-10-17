"""Integration tests for repositories, issues, and runs CRUD API endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_repository_crud_and_conflict(async_client: AsyncClient):
    repo_payload = {
        "github_repository_id": 99901,
        "full_name": "test-org/repo-alpha",
        "default_branch": "main",
        "description": "Alpha test repository",
    }
    # 1. Create repository
    res = await async_client.post("/api/v1/repositories", json=repo_payload)
    assert res.status_code == 201
    created_repo = res.json()
    assert created_repo["id"] is not None
    assert created_repo["full_name"] == "test-org/repo-alpha"

    # 2. Duplicate repository must fail with 409
    res_dup = await async_client.post("/api/v1/repositories", json=repo_payload)
    assert res_dup.status_code == 409

    # 3. List repositories
    list_res = await async_client.get("/api/v1/repositories?skip=0&limit=10")
    assert list_res.status_code == 200
    repos = list_res.json()
    assert len(repos) >= 1
    assert any(r["id"] == created_repo["id"] for r in repos)


@pytest.mark.asyncio
async def test_issue_crud_and_validation(async_client: AsyncClient):
    # Setup repository first
    repo_res = await async_client.post(
        "/api/v1/repositories",
        json={
            "github_repository_id": 99902,
            "full_name": "test-org/repo-beta",
            "default_branch": "develop",
        },
    )
    repo_id = repo_res.json()["id"]

    # 1. Ingest Issue
    issue_payload = {
        "repository_id": repo_id,
        "github_issue_number": 10,
        "title": "Fix login crash",
        "body": "Null pointer on empty email",
        "state": "open",
        "labels": ["bug", "auth"],
    }
    res = await async_client.post("/api/v1/issues", json=issue_payload)
    assert res.status_code == 201
    created_issue = res.json()
    assert created_issue["id"] is not None
    assert created_issue["github_issue_number"] == 10

    # 2. Duplicate issue in same repo must fail with 409
    dup_res = await async_client.post("/api/v1/issues", json=issue_payload)
    assert dup_res.status_code == 409

    # 3. Create issue for non-existent repo must return 404
    non_existent_payload = {
        "repository_id": "00000000-0000-0000-0000-000000000000",
        "github_issue_number": 11,
        "title": "Non-existent repo issue",
    }
    res_404 = await async_client.post("/api/v1/issues", json=non_existent_payload)
    assert res_404.status_code == 404

    # 4. List issues with repository filter
    list_res = await async_client.get(f"/api/v1/issues?repository_id={repo_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


@pytest.mark.asyncio
async def test_run_crud_lifecycle(async_client: AsyncClient):
    # Setup repo and issue
    repo_res = await async_client.post(
        "/api/v1/repositories",
        json={
            "github_repository_id": 99903,
            "full_name": "test-org/repo-gamma",
            "default_branch": "main",
        },
    )
    repo_id = repo_res.json()["id"]

    issue_res = await async_client.post(
        "/api/v1/issues",
        json={
            "repository_id": repo_id,
            "github_issue_number": 101,
            "title": "Fix pipeline timeout",
        },
    )
    issue_id = issue_res.json()["id"]

    # 1. Create Run
    run_payload = {
        "repository_id": repo_id,
        "issue_id": issue_id,
    }
    res = await async_client.post("/api/v1/runs", json=run_payload)
    assert res.status_code == 201
    run_data = res.json()
    run_id = run_data["id"]
    assert run_data["status"] == "QUEUED"
    assert run_data["current_node"] == "start"
    assert run_data["retry_count"] == 0

    # 2. Get Run by ID
    get_res = await async_client.get(f"/api/v1/runs/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == run_id

    # 3. Get non-existent Run returns 404
    missing_res = await async_client.get("/api/v1/runs/non-existent-run-id")
    assert missing_res.status_code == 404

    # 4. List runs
    list_res = await async_client.get(f"/api/v1/runs?repository_id={repo_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
