"""
Router: News Hunting & Raw Articles
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone

from backend.app.database import get_db_connection
from backend.app.models.article import ArticleOut
from backend.app.engines.hunter import run_news_hunter
from backend.app.engines.automation_worker import run_pipeline_for_article

router = APIRouter(prefix="/api/news", tags=["News"])
VN_TZ = timezone(timedelta(hours=7))

@router.post("/scan")
async def scan_news(
    category: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None)
):
    """Trigger news hunter across active sources."""
    result = await run_news_hunter(category=category, country=country, source_id=source_id)
    return result

@router.get("")
def list_articles(
    category: Optional[str] = None,
    country: Optional[str] = None,
    status: Optional[str] = None,
    time_range: Optional[str] = None, # 30m, 1h, 3h, 6h, today, 24h
    keyword: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List news articles with filters."""
    conn = get_db_connection()
    query = """
        SELECT articles.*, 
               (SELECT id FROM posts WHERE posts.article_id = articles.id ORDER BY id DESC LIMIT 1) as post_id,
               (SELECT status FROM posts WHERE posts.article_id = articles.id ORDER BY id DESC LIMIT 1) as post_status
        FROM articles 
        WHERE 1=1
    """
    params = []

    is_trending = False
    if category:
        if category == "Trending":
            is_trending = True
            query += " AND trend_score >= 70"
        else:
            query += " AND category = ?"
            params.append(category)
    if country:
        query += " AND country = ?"
        params.append(country)
    if status:
        query += " AND status = ?"
        params.append(status)
    if keyword:
        query += " AND (title LIKE ? OR summary LIKE ?)"
        kw = f"%{keyword}%"
        params.extend([kw, kw])

    if time_range:
        now_vn = datetime.now(VN_TZ)
        if time_range == "30m":
            cutoff = (now_vn - timedelta(minutes=30)).isoformat()
        elif time_range == "1h":
            cutoff = (now_vn - timedelta(hours=1)).isoformat()
        elif time_range == "3h":
            cutoff = (now_vn - timedelta(hours=3)).isoformat()
        elif time_range == "6h":
            cutoff = (now_vn - timedelta(hours=6)).isoformat()
        elif time_range == "today":
            cutoff = now_vn.replace(hour=0, minute=0, second=0).isoformat()
        elif time_range == "24h":
            cutoff = (now_vn - timedelta(hours=24)).isoformat()
        else:
            cutoff = None

        if cutoff:
            query += " AND collected_at >= ?"
            params.append(cutoff)

    if is_trending:
        query += " ORDER BY trend_score DESC, collected_at DESC LIMIT ? OFFSET ?"
    else:
        query += " ORDER BY (CASE WHEN country = 'VN' THEN 0 ELSE 1 END), collected_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # Normalize status: If an article was marked PROCESSED but no post exists, treat as NEW
        if d.get("status") == "PROCESSED" and not d.get("post_id"):
            d["status"] = "NEW"
        result.append(d)
    return result

@router.get("/{article_id}")
def get_article(article_id: int):
    """Get single article with attached media."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Article not found")

    article = dict(row)
    media_rows = conn.execute("SELECT * FROM media WHERE article_id = ?", (article_id,)).fetchall()
    article["media_items"] = [dict(m) for m in media_rows]
    conn.close()
    return article

@router.post("/{article_id}/process")
async def process_article(article_id: int):
    """Trigger the 12-step pipeline for an article."""
    result = await run_pipeline_for_article(article_id)
    return result

@router.post("/{article_id}/reject")
def reject_article(article_id: int, reason: str = Query("Bỏ qua bởi biên tập viên")):
    """Reject an article."""
    conn = get_db_connection()
    conn.execute("UPDATE articles SET status = 'REJECTED', hard_block_reason = ? WHERE id = ?", (reason, article_id))
    conn.commit()
    conn.close()
    return {"success": True, "article_id": article_id, "status": "REJECTED"}
