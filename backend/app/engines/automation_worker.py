"""
LIFE TODAY — AI NEWSROOM V1.0
Automation Engine: 12-Step Autonomous Newsroom Pipeline Worker
"""
import asyncio
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from backend.app.database import get_db_connection, get_setting, log_audit
from backend.app.engines.hunter import run_news_hunter
from backend.app.engines.hard_block import evaluate_hard_block
from backend.app.engines.fact_checker import verify_facts_and_compliance
from backend.app.engines.caption_engine import generate_caption_ai
from backend.app.engines.deduplication import check_duplicate_article
from backend.app.engines.scheduler import schedule_post_to_slot
from backend.app.engines.facebook_publisher import FacebookPublisher

VN_TZ = timezone(timedelta(hours=7))

async def run_pipeline_for_article(article_id: int) -> Dict:
    """
    Run full 12-step validation, media curation, caption generation,
    and post draft creation for a single news article.
    """
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": f"Article #{article_id} not found"}
    article = dict(row)

    now_iso = datetime.now(VN_TZ).isoformat()
    operating_mode = get_setting("operating_mode", "SHADOW_MODE")
    emergency_stop = get_setting("emergency_stop", "false").lower() == "true"

    if emergency_stop:
        conn.close()
        return {"success": False, "error": "EMERGENCY_STOP is active. Aborting pipeline."}

    # Step 1 & 2: Deduplication (exclude current article id)
    is_dup, dup_reason = check_duplicate_article(article["canonical_url"], article["title"], exclude_id=article_id)
    if is_dup:
        conn.execute("UPDATE articles SET status = 'REJECTED', hard_block_reason = ? WHERE id = ?", (dup_reason, article_id))
        conn.commit()
        conn.close()
        return {"success": False, "step": "DEDUPLICATION", "reason": dup_reason}

    # Step 3: Hard Block Evaluation
    is_blocked, block_reason, _ = evaluate_hard_block(article["title"], article.get("summary", ""), article.get("content", ""))
    if is_blocked:
        conn.execute("UPDATE articles SET status = 'HOLD', hard_block_reason = ? WHERE id = ?", (block_reason, article_id))
        conn.commit()
        conn.close()
        return {"success": False, "step": "HARD_BLOCK", "reason": block_reason}

    # Step 4: Fact Checking & Compliance
    source_rel = 0.90
    if article.get("source_id"):
        s_row = conn.execute("SELECT reliability_score FROM sources WHERE id = ?", (article["source_id"],)).fetchone()
        if s_row:
            source_rel = s_row["reliability_score"]

    fact_status, fact_meta = verify_facts_and_compliance(
        article["title"],
        article.get("summary", ""),
        source_rel
    )
    if fact_status != "VERIFIED":
        conn.execute("UPDATE articles SET status = 'HOLD', hard_block_reason = ? WHERE id = ?", ("; ".join(fact_meta.get("notes", [])), article_id))
        conn.commit()
        conn.close()
        return {"success": False, "step": "FACT_CHECK", "reason": "; ".join(fact_meta.get("notes", []))}

    # Step 5, 6, 7: Media Extraction & Quality Check
    media_rows = conn.execute("SELECT * FROM media WHERE article_id = ?", (article_id,)).fetchall()
    qualified_media = [m for m in media_rows if m["quality_status"] == "QUALIFIED"]

    # Step 8: AI Caption Synthesis
    caption_res = await generate_caption_ai(
        title=article["title"],
        summary=article.get("summary", ""),
        category=article.get("category", "Showbiz"),
        entities=fact_meta.get("entities"),
        credit_source=article.get("source_name", "")
    )

    # Step 9: Create Post Record
    post_uuid = hashlib.sha256(f"post_{article_id}_{now_iso}".encode()).hexdigest()
    post_type = "ORIGINAL_PHOTO_POST" if qualified_media else "TEXT_POST"

    initial_status = "PENDING_REVIEW"
    if operating_mode == "SHADOW_MODE":
        initial_status = "PENDING_REVIEW"
    elif operating_mode == "FULL_AUTO":
        initial_status = "APPROVED"

    # Auto-attach source article link by default
    post_caption = caption_res["caption"]
    if article.get("url"):
        post_caption = f"{post_caption}\n\n👉 Xem chi tiết tại: {article['url']}"

    # Remove any previous un-published draft for this article
    conn.execute("DELETE FROM posts WHERE article_id = ? AND status IN ('PENDING_REVIEW', 'FAILED', 'HOLD')", (article_id,))

    cursor = conn.execute("""
        INSERT INTO posts (
            post_uuid, article_id, post_type, category, caption, hashtags,
            credit_source, status, operating_mode, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_uuid, article_id, post_type, article["category"],
        post_caption, caption_res["hashtags"], caption_res["credit_line"],
        initial_status, operating_mode, now_iso, now_iso
    ))
    post_id = cursor.lastrowid

    # Associate media items with post
    for m in media_rows:
        conn.execute("UPDATE media SET post_id = ? WHERE id = ?", (post_id, m["id"]))

    conn.execute("UPDATE articles SET status = 'PROCESSED', verified_at = ? WHERE id = ?", (now_iso, article_id))
    conn.commit()
    conn.close()

    # Step 10: Scheduling / Execution depending on mode
    sched_info = None
    if operating_mode in ("FULL_AUTO", "SHADOW_MODE"):
        sched_info = schedule_post_to_slot(post_id)

    log_audit("PIPELINE_COMPLETE", "AUTOMATION_WORKER", f"Processed article #{article_id} -> Post #{post_id} ({initial_status})")

    return {
        "success": True,
        "article_id": article_id,
        "post_id": post_id,
        "post_uuid": post_uuid,
        "status": initial_status,
        "caption": caption_res["caption"],
        "hashtags": caption_res["hashtags"],
        "scheduling": sched_info
    }

async def run_autonomous_cycle(category_filter: Optional[str] = None) -> Dict:
    """Execute complete autonomous cycle across active sources."""
    # 1. Hunt
    hunt_res = await run_news_hunter(category=category_filter)
    new_articles = hunt_res.get("articles", [])

    # 2. Process each new article
    processed_posts = []
    for art in new_articles:
        p_res = await run_pipeline_for_article(art["id"])
        if p_res.get("success"):
            processed_posts.append(p_res)

    log_audit("CYCLE_COMPLETE", "AUTOMATION_WORKER", f"Scanned {hunt_res['sources_scanned']} sources, processed {len(processed_posts)} posts")

    return {
        "sources_scanned": hunt_res["sources_scanned"],
        "new_articles_count": len(new_articles),
        "posts_created_count": len(processed_posts),
        "posts": processed_posts
    }
