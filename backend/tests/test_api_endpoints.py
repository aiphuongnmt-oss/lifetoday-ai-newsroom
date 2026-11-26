"""
FastAPI In-Memory Endpoint Integration Tests
"""
import asyncio
import httpx
from backend.app.main import app

async def test_all_routes():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        res = await client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ONLINE"
        print("[PASSED] GET /api/health -> 200 OK")

        # 2. Settings status
        res = await client.get("/api/settings/status")
        assert res.status_code == 200
        data = res.json()
        assert "operating_mode" in data
        assert data["app_name"] == "LIFE TODAY — AI NEWSROOM"
        print(f"[PASSED] GET /api/settings/status -> Mode: {data['operating_mode']}")

        # 3. Source Registry
        res = await client.get("/api/sources")
        assert res.status_code == 200
        sources = res.json()
        assert len(sources) >= 10
        print(f"[PASSED] GET /api/sources -> {len(sources)} sources")

        # 4. Articles
        res = await client.get("/api/news")
        assert res.status_code == 200
        articles = res.json()
        print(f"[PASSED] GET /api/news -> {len(articles)} articles")

        # 5. Posts
        res = await client.get("/api/posts")
        assert res.status_code == 200
        posts = res.json()
        print(f"[PASSED] GET /api/posts -> {len(posts)} posts")

        # 6. Media
        res = await client.get("/api/media")
        assert res.status_code == 200
        media = res.json()
        print(f"[PASSED] GET /api/media -> {len(media)} media records")

        # 7. Analytics Content Mix
        res = await client.get("/api/analytics/mix")
        assert res.status_code == 200
        mix = res.json()
        assert "targets" in mix
        print(f"[PASSED] GET /api/analytics/mix -> Targets verified")

        # 8. Audit Logs
        res = await client.get("/api/analytics/logs")
        assert res.status_code == 200
        logs = res.json()
        assert len(logs) > 0
        print(f"[PASSED] GET /api/analytics/logs -> {len(logs)} audit logs")

        # 9. Frontend Root
        res = await client.get("/")
        assert res.status_code == 200
        assert "LIFE TODAY" in res.text
        print("[PASSED] GET / (Frontend Dashboard) -> 200 OK")

    print("ALL API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_all_routes())
