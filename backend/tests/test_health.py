import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health(async_client: AsyncClient):
    """Verify /health endpoint returns healthy status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "project" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_api_v1_health(async_client: AsyncClient):
    """Verify /api/v1/health endpoint returns healthy status."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_v1_system_status(async_client: AsyncClient):
    """Verify /api/v1/system/status diagnostic endpoint."""
    response = await async_client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["database_connected"] is True
    assert "environment" in data
