"""
LIFE TODAY — AI NEWSROOM V1.0
Storage Cleaner & Data Retention Engine
- Enforces strict 24-hour freshness window.
- Auto-purges unused raw articles (> 24 hours old).
- Cleans up orphan / discarded media files from disk.
- Removes local media files for posts already published to Facebook (since Meta stores them forever on CDN).
- Runs SQLite VACUUM to reclaim disk space.
"""
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict

from backend.app.config import DB_PATH, MEDIA_DIR
from backend.app.database import get_db_connection, log_audit

VN_TZ = timezone(timedelta(hours=7))

def get_storage_stats() -> Dict:
    """Calculate current database and media disk usage."""
    db_size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    media_files = list(MEDIA_DIR.glob("*")) if MEDIA_DIR.exists() else []
    media_size_bytes = sum(f.stat().st_size for f in media_files if f.is_file())

    conn = get_db_connection()
    articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    posts_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    scheduled_count = conn.execute("SELECT COUNT(*) FROM posts WHERE status = 'SCHEDULED'").fetchone()[0]
    published_count = conn.execute("SELECT COUNT(*) FROM posts WHERE status IN ('PUBLISHED', 'SHADOW_PUBLISHED')").fetchone()[0]
    media_count = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    conn.close()

    return {
        "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
        "media_size_mb": round(media_size_bytes / (1024 * 1024), 2),
        "total_size_mb": round((db_size_bytes + media_size_bytes) / (1024 * 1024), 2),
        "media_files_on_disk": len(media_files),
        "articles_count": articles_count,
        "posts_count": posts_count,
        "scheduled_count": scheduled_count,
        "published_count": published_count,
        "media_records": media_count
    }

def run_storage_cleanup(
    max_raw_article_age_hours: int = 24,
    purge_published_local_media: bool = True
) -> Dict:
    """
    Execute full storage hygiene:
    1. Purge raw un-curated articles older than max_raw_article_age_hours (default 24h).
    2. Delete orphan media records and their files from disk.
    3. Remove local image files for posts already published on Facebook.
    4. Compact SQLite database with VACUUM.
    """
    conn = get_db_connection()
    now_vn = datetime.now(VN_TZ)
    cutoff_raw = (now_vn - timedelta(hours=max_raw_article_age_hours)).isoformat()

    # 1. Find raw un-processed articles older than cutoff (status = 'NEW' or 'REJECTED')
    old_articles = conn.execute("""
        SELECT id FROM articles
        WHERE collected_at < ? AND status IN ('NEW', 'REJECTED')
        AND id NOT IN (SELECT article_id FROM posts WHERE article_id IS NOT NULL)
    """, (cutoff_raw,)).fetchall()
    old_art_ids = [r[0] for r in old_articles]

    purged_articles = len(old_art_ids)
    if old_art_ids:
        placeholders = ",".join("?" * len(old_art_ids))
        # Find local files to delete
        media_to_delete = conn.execute(f"SELECT local_path FROM media WHERE article_id IN ({placeholders})", old_art_ids).fetchall()
        for m in media_to_delete:
            p = m["local_path"]
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        conn.execute(f"DELETE FROM media WHERE article_id IN ({placeholders})", old_art_ids)
        conn.execute(f"DELETE FROM articles WHERE id IN ({placeholders})", old_art_ids)
        conn.commit()

    # 2. Cleanup local files for published posts (since Facebook CDN already stores them)
    cleaned_published_files = 0
    if purge_published_local_media:
        published_media = conn.execute("""
            SELECT m.id, m.local_path FROM media m
            JOIN posts p ON (m.post_id = p.id OR m.article_id = p.article_id)
            WHERE p.status IN ('PUBLISHED', 'SHADOW_PUBLISHED') AND m.local_path IS NOT NULL
        """).fetchall()

        for pm in published_media:
            p = pm["local_path"]
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                    cleaned_published_files += 1
                except Exception:
                    pass
            # Clear local path from DB but keep original URL
            conn.execute("UPDATE media SET local_path = NULL WHERE id = ?", (pm["id"],))
        conn.commit()

    # 3. Delete any orphaned media records
    conn.execute("DELETE FROM media WHERE article_id IS NOT NULL AND article_id NOT IN (SELECT id FROM articles)")
    conn.commit()

    # 4. Clean orphan files on disk that have no record in DB
    valid_paths = set(r[0] for r in conn.execute("SELECT local_path FROM media WHERE local_path IS NOT NULL").fetchall())
    orphan_files_deleted = 0
    if MEDIA_DIR.exists():
        for f in MEDIA_DIR.glob("*"):
            if f.is_file() and str(f) not in valid_paths:
                try:
                    f.unlink()
                    orphan_files_deleted += 1
                except Exception:
                    pass

    conn.close()

    # 5. SQLite VACUUM to reclaim free disk space
    try:
        raw_conn = sqlite3.connect(str(DB_PATH))
        raw_conn.execute("VACUUM")
        raw_conn.close()
    except Exception as e:
        print(f"VACUUM error: {e}")

    log_audit(
        "STORAGE_CLEANUP",
        "STORAGE_CLEANER",
        f"Purged {purged_articles} old raw articles, {cleaned_published_files} published media files, {orphan_files_deleted} orphan files"
    )

    return {
        "purged_articles_count": purged_articles,
        "cleaned_published_files": cleaned_published_files,
        "orphan_files_deleted": orphan_files_deleted,
        "new_stats": get_storage_stats()
    }
