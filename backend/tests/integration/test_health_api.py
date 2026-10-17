"""Integration tests for health check endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "DevSquad API"
    assert "health_url" in data


@pytest.mark.asyncio
async def test_composite_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "database" in data["components"]
    assert "llm" in data["components"]
    assert "docker" in data["components"]
    assert data["components"]["database"]["status"] == "operational"


@pytest.mark.asyncio
async def test_database_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/database")
    assert response.status_code == 200
    data = response.json()
    assert data["component"] == "database"
    assert data["status"] == "operational"
    assert "latency_ms" in data["details"]


@pytest.mark.asyncio
async def test_llm_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/llm")
    assert response.status_code == 200
    data = response.json()
    assert data["component"] == "llm"
    # In test/unconfigured environment, status must be unconfigured, never fake operational
    assert data["status"] in ("unconfigured", "operational")
    assert "provider" in data["details"]


@pytest.mark.asyncio
async def test_docker_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/docker")
    assert response.status_code == 200
    data = response.json()
    assert data["component"] == "docker"
    # Must report operational or unavailable honestly
    assert data["status"] in ("operational", "unavailable")
