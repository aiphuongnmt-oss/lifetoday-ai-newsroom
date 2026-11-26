"""
Targeted Database Purification: Pure Vietnamese Entertainment, Fashion, Travel & Cuisine
"""
from backend.app.database import get_db_connection
from backend.app.engines.hard_block import evaluate_hard_block

def purify():
    conn = get_db_connection()

    # 1. Delete all non-VN records
    conn.execute("DELETE FROM posts WHERE article_id IN (SELECT id FROM articles WHERE country != 'VN')")
    conn.execute("DELETE FROM media WHERE article_id IN (SELECT id FROM articles WHERE country != 'VN')")
    conn.execute("DELETE FROM articles WHERE country != 'VN'")
    conn.commit()
    print("Deleted all non-VN articles.")

    # 2. Delete articles that match sensitive life, social, court, or accident topics
    all_vn = conn.execute("SELECT id, title, summary, content FROM articles").fetchall()
    blocked_ids = []
    for a in all_vn:
        is_blocked, reason, _ = evaluate_hard_block(a["title"], a["summary"] or "", a["content"] or "")
        if is_blocked:
            blocked_ids.append(a["id"])

    if blocked_ids:
        placeholders = ",".join("?" * len(blocked_ids))
        conn.execute(f"DELETE FROM posts WHERE article_id IN ({placeholders})", blocked_ids)
        conn.execute(f"DELETE FROM media WHERE article_id IN ({placeholders})", blocked_ids)
        conn.execute(f"DELETE FROM articles WHERE id IN ({placeholders})", blocked_ids)
        conn.commit()
        print(f"Purged {len(blocked_ids)} articles matching politics/social/sensitive rules.")

    # 3. Clean up orphaned posts
    conn.execute("DELETE FROM posts WHERE article_id IS NOT NULL AND article_id NOT IN (SELECT id FROM articles)")
    conn.commit()

    # 4. Count remaining
    art_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    post_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    sched_count = conn.execute("SELECT COUNT(*) FROM posts WHERE status = 'SCHEDULED'").fetchone()[0]
    cat_counts = conn.execute("SELECT category, COUNT(*) FROM articles GROUP BY category").fetchall()
    conn.close()

    print("\n" + "=" * 60)
    print("PURIFIED DATABASE STATE:")
    print(f"- Total Clean Vietnamese Articles: {art_count}")
    print(f"- Total Clean Posts: {post_count} (Scheduled: {sched_count})")
    print("Categories:")
    for cat, count in cat_counts:
        print(f"  * {cat}: {count} articles")
    print("=" * 60)

if __name__ == "__main__":
    purify()
