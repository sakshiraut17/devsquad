import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


async def test_live_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # Call GET /health
        res_health = await client.get("/health")
        print("GET /health -> Status Code:", res_health.status_code)
        print("Response JSON:", res_health.json())
        print("-" * 50)

        # Call GET /api/v1/health
        res_v1_health = await client.get("/api/v1/health")
        print("GET /api/v1/health -> Status Code:", res_v1_health.status_code)
        print("Response JSON:", res_v1_health.json())
        print("-" * 50)

        # Call GET /api/v1/system/status
        res_system = await client.get("/api/v1/system/status")
        print("GET /api/v1/system/status -> Status Code:", res_system.status_code)
        print("Response JSON:", res_system.json())


if __name__ == "__main__":
    asyncio.run(test_live_endpoints())
