"""
Purge Non-VN & Social News, Re-hunt Pure Vietnamese Entertainment, Fashion, Travel & Food
"""
import asyncio
from backend.app.database import get_db_connection, init_db
from backend.app.engines.source_registry import seed_source_registry
from backend.app.engines.hard_block import evaluate_hard_block
from backend.app.engines.hunter import run_news_hunter
from backend.app.engines.automation_worker import run_pipeline_for_article

def purge_non_lifestyle():
    conn = get_db_connection()
    # Delete non-VN
    conn.execute("DELETE FROM posts WHERE article_id IN (SELECT id FROM articles WHERE country != 'VN')")
    conn.execute("DELETE FROM media WHERE article_id IN (SELECT id FROM articles WHERE country != 'VN')")
    conn.execute("DELETE FROM articles WHERE country != 'VN'")
    conn.commit()

    # Scan VN articles against enhanced Hard Block rules
    vn_articles = conn.execute("SELECT id, title, summary, content FROM articles").fetchall()
    blocked_ids = []
    for a in vn_articles:
        is_blocked, reason, cat = evaluate_hard_block(a["title"], a["summary"] or "", a["content"] or "")
        if is_blocked:
            blocked_ids.append(a["id"])

    if blocked_ids:
        placeholders = ",".join("?" * len(blocked_ids))
        conn.execute(f"DELETE FROM posts WHERE article_id IN ({placeholders})", blocked_ids)
        conn.execute(f"DELETE FROM media WHERE article_id IN ({placeholders})", blocked_ids)
        conn.execute(f"DELETE FROM articles WHERE id IN ({placeholders})", blocked_ids)
        conn.commit()

    conn.close()
    seed_source_registry()
    print(f"Purged {len(blocked_ids)} articles matching politics/social/sensitive rules.")

async def rehunt_vn():
    print("Fetching fresh pure Vietnamese lifestyle feeds...")
    res = await run_news_hunter(country="VN")
    print(f"Scanned {res['sources_scanned']} VN sources, found {res['new_articles_count']} new articles.")

    for art in res.get("articles", []):
        await run_pipeline_for_article(art["id"])

    conn = get_db_connection()
    print("Final Count:", conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0], "articles.")
    conn.close()

if __name__ == "__main__":
    purge_non_lifestyle()
    asyncio.run(rehunt_vn())
