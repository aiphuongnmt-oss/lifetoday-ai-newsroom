"""
LIFE TODAY — AI NEWSROOM V1.0
Source Registry Engine: 100% Vietnamese Official Lifestyle, Entertainment, Fashion, Travel & Food Feeds
"""
from datetime import datetime
from typing import Dict, List, Optional
import httpx
from backend.app.database import get_db_connection, log_audit

DEFAULT_SOURCES: List[Dict] = [
    # 1. VnExpress
    {
        "id": "vn_vnexpress_giaitri",
        "name": "VnExpress Giải Trí",
        "url": "https://vnexpress.net/giai-tri",
        "feed_url": "https://vnexpress.net/rss/giai-tri.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Showbiz",
        "reliability_score": 0.98,
        "rate_limit_seconds": 60,
    },
    {
        "id": "vn_vnexpress_dulich",
        "name": "VnExpress Du Lịch",
        "url": "https://vnexpress.net/du-lich",
        "feed_url": "https://vnexpress.net/rss/du-lich.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Du lịch",
        "reliability_score": 0.98,
        "rate_limit_seconds": 60,
    },
    # 2. Chuyên trang Ngôi Sao (VnExpress) - Hậu trường, Thời trang, Ăn chơi
    {
        "id": "vn_ngoisao_thoitrang",
        "name": "Ngôi Sao Thời Trang & Làm Đẹp",
        "url": "https://ngoisao.vnexpress.net/thoi-trang",
        "feed_url": "https://ngoisao.vnexpress.net/rss/thoi-trang.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Thời trang và làm đẹp",
        "reliability_score": 0.96,
        "rate_limit_seconds": 60,
    },
    {
        "id": "vn_ngoisao_hautruong",
        "name": "Ngôi Sao Showbiz",
        "url": "https://ngoisao.vnexpress.net/hau-truong",
        "feed_url": "https://ngoisao.vnexpress.net/rss/hau-truong.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Showbiz",
        "reliability_score": 0.96,
        "rate_limit_seconds": 60,
    },
    {
        "id": "vn_ngoisao_anchoi",
        "name": "Ngôi Sao Ẩm Thực & Trải Nghiệm",
        "url": "https://ngoisao.vnexpress.net/an-choi",
        "feed_url": "https://ngoisao.vnexpress.net/rss/an-choi.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Ẩm thực",
        "reliability_score": 0.96,
        "rate_limit_seconds": 60,
    },
    # 3. Thanh Niên
    {
        "id": "vn_thanhnien_giaitri",
        "name": "Thanh Niên Giải Trí",
        "url": "https://thanhnien.vn/giai-tri.html",
        "feed_url": "https://thanhnien.vn/rss/giai-tri.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Showbiz",
        "reliability_score": 0.95,
        "rate_limit_seconds": 60,
    },
    {
        "id": "vn_thanhnien_dulich",
        "name": "Thanh Niên Du Lịch",
        "url": "https://thanhnien.vn/du-lich.html",
        "feed_url": "https://thanhnien.vn/rss/du-lich.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Du lịch",
        "reliability_score": 0.95,
        "rate_limit_seconds": 60,
    },
    # 4. Tuổi Trẻ
    {
        "id": "vn_tuoitre_giaitri",
        "name": "Tuổi Trẻ Giải Trí",
        "url": "https://tuoitre.vn/giai-tri.htm",
        "feed_url": "https://tuoitre.vn/rss/giai-tri.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Showbiz",
        "reliability_score": 0.95,
        "rate_limit_seconds": 60,
    },
    {
        "id": "vn_tuoitre_dulich",
        "name": "Tuổi Trẻ Du Lịch",
        "url": "https://tuoitre.vn/du-lich.htm",
        "feed_url": "https://tuoitre.vn/rss/du-lich.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Du lịch",
        "reliability_score": 0.95,
        "rate_limit_seconds": 60,
    },
    # 5. Dân Trí
    {
        "id": "vn_dantri_giaitri",
        "name": "Dân Trí Giải Trí",
        "url": "https://dantri.com.vn/giai-tri.htm",
        "feed_url": "https://dantri.com.vn/rss/giai-tri.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Showbiz",
        "reliability_score": 0.94,
        "rate_limit_seconds": 60,
    },
    {
        "id": "vn_dantri_dulich",
        "name": "Dân Trí Du Lịch",
        "url": "https://dantri.com.vn/du-lich.htm",
        "feed_url": "https://dantri.com.vn/rss/du-lich.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Du lịch",
        "reliability_score": 0.94,
        "rate_limit_seconds": 60,
    },
    # 6. VietnamNet
    {
        "id": "vn_vietnamnet_giaitri",
        "name": "VietnamNet Giải Trí",
        "url": "https://vietnamnet.vn/giai-tri",
        "feed_url": "https://vietnamnet.vn/rss/giai-tri.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Showbiz",
        "reliability_score": 0.94,
        "rate_limit_seconds": 60,
    },
    {
        "id": "vn_vietnamnet_dulich",
        "name": "VietnamNet Du Lịch",
        "url": "https://vietnamnet.vn/du-lich",
        "feed_url": "https://vietnamnet.vn/rss/du-lich.rss",
        "country": "VN",
        "language": "vi",
        "default_category": "Du lịch",
        "reliability_score": 0.94,
        "rate_limit_seconds": 60,
    }
]

def seed_source_registry() -> None:
    """Populate default reputable Vietnamese sources into the SQLite registry."""
    conn = get_db_connection()
    now_iso = datetime.now().isoformat()
    # Deactivate any non-VN sources
    conn.execute("UPDATE sources SET is_active = 0 WHERE country != 'VN'")

    for s in DEFAULT_SOURCES:
        conn.execute("""
            INSERT INTO sources (
                id, name, url, feed_url, country, language, default_category,
                reliability_score, rate_limit_seconds, is_active, last_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'ACTIVE', ?)
            ON CONFLICT(id) DO UPDATE SET
                feed_url = excluded.feed_url,
                default_category = excluded.default_category,
                reliability_score = excluded.reliability_score,
                is_active = 1
        """, (
            s["id"], s["name"], s["url"], s.get("feed_url"), s["country"],
            s["language"], s["default_category"], s["reliability_score"],
            s["rate_limit_seconds"], now_iso
        ))
    conn.commit()
    conn.close()

def get_all_sources(active_only: bool = True) -> List[Dict]:
    """Retrieve sources from database."""
    conn = get_db_connection()
    query = "SELECT * FROM sources"
    if active_only:
        query += " WHERE is_active = 1 AND country = 'VN'"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def check_source_health(source_id: str) -> Dict:
    """Perform real health check against a source's feed."""
    conn = get_db_connection()
    source = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    if not source:
        conn.close()
        return {"status": "NOT_FOUND", "message": "Source not registered"}

    feed_url = source["feed_url"]
    status = "ERROR"
    status_code = None
    now_iso = datetime.now().isoformat()

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.head(feed_url or source["url"])
            status_code = resp.status_code
            if status_code in (200, 301, 302):
                status = "HEALTHY"
            else:
                status = f"HTTP_{status_code}"
    except Exception as e:
        status = f"FAILED: {str(e)[:50]}"

    conn.execute(
        "UPDATE sources SET last_checked_at = ?, last_status = ? WHERE id = ?",
        (now_iso, status, source_id)
    )
    conn.commit()
    conn.close()

    log_audit("SOURCE_HEALTH_CHECK", "SOURCE_REGISTRY", f"{source_id}: {status}")
    return {"source_id": source_id, "status": status, "http_code": status_code, "checked_at": now_iso}
