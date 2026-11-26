"""
Inspect Database State
"""
from backend.app.database import get_db_connection

def main():
    conn = get_db_connection()
    articles_count = conn.execute("SELECT COUNT(*) as c FROM articles").fetchone()["c"]
    posts_count = conn.execute("SELECT COUNT(*) as c FROM posts").fetchone()["c"]
    scheduled_count = conn.execute("SELECT COUNT(*) as c FROM posts WHERE status = 'SCHEDULED'").fetchone()["c"]
    pending_count = conn.execute("SELECT COUNT(*) as c FROM posts WHERE status = 'PENDING_REVIEW'").fetchone()["c"]
    media_count = conn.execute("SELECT COUNT(*) as c FROM media").fetchone()["c"]

    print("=" * 60)
    print("LIVE DATABASE STATUS")
    print("=" * 60)
    print(f"Articles in Database: {articles_count}")
    print(f"Total Posts Created: {posts_count}")
    print(f"Scheduled Posts: {scheduled_count}")
    print(f"Pending Posts: {pending_count}")
    print(f"Media Extracted: {media_count}")

    print("\nSAMPLE SCHEDULED POSTS IN THE 6 SLOTS:")
    rows = conn.execute("SELECT id, category, target_slot, scheduled_time, caption, hashtags FROM posts WHERE status = 'SCHEDULED' LIMIT 6").fetchall()
    for r in rows:
        print(f" * Post #{r['id']} [{r['category']}] -> Khung {r['target_slot']} ({r['scheduled_time']})")
        print(f"   Caption: {r['caption']}")
        print(f"   Tags: {r['hashtags']}\n")

if __name__ == "__main__":
    main()
