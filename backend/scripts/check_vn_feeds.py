"""
Test Vietnamese Feeds
"""
import asyncio
import httpx
from backend.app.engines.source_registry import DEFAULT_SOURCES

async def check():
    headers = {"User-Agent": "Mozilla/5.0"}
    for s in DEFAULT_SOURCES:
        url = s.get("feed_url")
        try:
            async with httpx.AsyncClient(timeout=4.0, headers=headers) as c:
                r = await c.head(url)
                print(f"{s['id']}: {r.status_code}")
        except Exception as e:
            print(f"{s['id']}: ERROR {str(e)[:40]}")

if __name__ == "__main__":
    asyncio.run(check())
