"""
Router: Posts Management & Facebook Publishing
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from datetime import datetime

from backend.app.database import get_db_connection, get_setting, log_audit
from backend.app.models.post import PostUpdate
from backend.app.engines.scheduler import schedule_post_to_slot
from backend.app.engines.facebook_publisher import FacebookPublisher

router = APIRouter(prefix="/api/posts", tags=["Posts"])

@router.get("")
def list_posts(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List posts with filters and attached media."""
    conn = get_db_connection()
    query = """
        SELECT p.*, a.url as article_url, a.title as article_title, a.source_name as article_source_name
        FROM posts p
        LEFT JOIN articles a ON p.article_id = a.id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND p.status = ?"
        params.append(status)
    if category:
        query += " AND p.category = ?"
        params.append(category)

    query += " ORDER BY p.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    posts = []
    for r in rows:
        p = dict(r)
        media_rows = conn.execute("SELECT * FROM media WHERE post_id = ? OR article_id = ?", (p["id"], p["article_id"])).fetchall()
        p["media_items"] = [dict(m) for m in media_rows]
        posts.append(p)

    conn.close()
    return posts

@router.get("/{post_id}")
def get_post(post_id: int):
    """Get post detail."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Post not found")

    post = dict(row)
    media_rows = conn.execute("SELECT * FROM media WHERE post_id = ? OR article_id = ?", (post["id"], post["article_id"])).fetchall()
    post["media_items"] = [dict(m) for m in media_rows]
    conn.close()
    return post

@router.put("/{post_id}")
def update_post(post_id: int, payload: PostUpdate):
    """Update post caption, hashtags, credit, or schedule time."""
    conn = get_db_connection()
    updates = []
    params = []

    if payload.caption is not None:
        updates.append("caption = ?")
        params.append(payload.caption)
    if payload.hashtags is not None:
        updates.append("hashtags = ?")
        params.append(payload.hashtags)
    if payload.credit_source is not None:
        updates.append("credit_source = ?")
        params.append(payload.credit_source)
    if payload.status is not None:
        updates.append("status = ?")
        params.append(payload.status)
    if payload.scheduled_time is not None:
        updates.append("scheduled_time = ?")
        params.append(payload.scheduled_time)
    if payload.target_slot is not None:
        updates.append("target_slot = ?")
        params.append(payload.target_slot)

    if not updates:
        conn.close()
        return {"success": True, "message": "No changes requested"}

    updates.append("updated_at = datetime('now')")
    params.append(post_id)

    query = f"UPDATE posts SET {', '.join(updates)} WHERE id = ?"
    conn.execute(query, params)
    conn.commit()
    conn.close()

    log_audit("POST_EDITED", "POSTS_ROUTER", f"Post #{post_id} updated")
    return {"success": True, "post_id": post_id}

@router.post("/{post_id}/approve")
def approve_post(post_id: int):
    """Approve a pending post."""
    conn = get_db_connection()
    conn.execute("UPDATE posts SET status = 'APPROVED', updated_at = datetime('now') WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    log_audit("POST_APPROVED", "POSTS_ROUTER", f"Post #{post_id} approved")
    return {"success": True, "post_id": post_id, "status": "APPROVED"}

@router.post("/{post_id}/publish")
async def publish_now(post_id: int):
    """Publish immediately (real FB publish or shadow publish based on operating mode)."""
    operating_mode = get_setting("operating_mode", "SHADOW_MODE")
    emergency_stop = get_setting("emergency_stop", "false").lower() == "true"

    pub = FacebookPublisher()
    res = await pub.publish_or_schedule_post(post_id, operating_mode=operating_mode, emergency_stop=emergency_stop)
    return res

@router.post("/{post_id}/schedule")
def schedule_post(post_id: int, custom_time: Optional[str] = Query(None)):
    """Assign post to next optimal slot or custom time."""
    result = schedule_post_to_slot(post_id, custom_time=custom_time)
    return result

@router.post("/{post_id}/cancel")
def cancel_post(post_id: int):
    """Cancel a scheduled or pending post."""
    conn = get_db_connection()
    conn.execute("UPDATE posts SET status = 'CANCELLED', updated_at = datetime('now') WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    log_audit("POST_CANCELLED", "POSTS_ROUTER", f"Post #{post_id} cancelled")
    return {"success": True, "post_id": post_id, "status": "CANCELLED"}

@router.delete("/{post_id}")
def delete_post(post_id: int):
    """Permanently delete a post and free its article."""
    conn = get_db_connection()
    post = conn.execute("SELECT article_id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post and post["article_id"]:
        # Reset article status so it can be re-used or created cleanly
        conn.execute("UPDATE articles SET status = 'NEW' WHERE id = ?", (post["article_id"],))
    conn.execute("DELETE FROM media WHERE post_id = ?", (post_id,))
    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    log_audit("POST_DELETED", "POSTS_ROUTER", f"Post #{post_id} deleted permanently")
    return {"success": True, "post_id": post_id}

@router.post("/{post_id}/regenerate-caption")
async def regenerate_caption(post_id: int):
    """Regenerate caption for an existing post using Gemini AI."""
    conn = get_db_connection()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Post not found")

    article = None
    if post["article_id"]:
        a_row = conn.execute("SELECT * FROM articles WHERE id = ?", (post["article_id"],)).fetchone()
        if a_row:
            article = dict(a_row)

    title = article["title"] if article else post["caption"]
    summary = article.get("summary", "") if article else ""

    from backend.app.engines.caption_engine import generate_caption_ai
    res = await generate_caption_ai(
        title=title,
        summary=summary,
        category=post["category"],
        credit_source=post["credit_source"] or (article.get("source_name", "") if article else "")
    )

    new_caption = res["caption"]
    if article and article.get("url"):
        new_caption = f"{new_caption}\n\n👉 Xem chi tiết tại: {article['url']}"

    conn.execute(
        "UPDATE posts SET caption = ?, hashtags = ?, updated_at = datetime('now') WHERE id = ?",
        (new_caption, res["hashtags"], post_id)
    )
    conn.commit()
    conn.close()

    log_audit("CAPTION_REGENERATED", "POSTS_ROUTER", f"Post #{post_id} caption regenerated via {res['engine_used']}")
    return {
        "success": True,
        "caption": new_caption,
        "hashtags": res["hashtags"],
        "credit_line": res.get("credit_line", ""),
        "engine_used": res.get("engine_used", "AI")
    }
