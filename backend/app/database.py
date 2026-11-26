"""
LIFE TODAY — AI NEWSROOM V1.0
Database Management (SQLite Canonical Storage)
"""
import os
import sqlite3
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.app.config import DB_PATH, DEFAULT_OPERATING_MODE, DEFAULT_CONTENT_MIX

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db() -> None:
    """Initialize database tables, indexes, and default settings."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Articles table (Raw collected & verified news)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guid TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        summary TEXT,
        content TEXT,
        url TEXT NOT NULL,
        canonical_url TEXT,
        source_id TEXT,
        source_name TEXT,
        country TEXT,
        language TEXT,
        category TEXT,
        published_at TEXT,
        collected_at TEXT,
        verified_at TEXT,
        trend_score REAL DEFAULT 0.0,
        trend_breakdown TEXT,
        status TEXT DEFAULT 'NEW',
        hard_block_reason TEXT,
        raw_data TEXT,
        created_at TEXT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_canonical ON articles(canonical_url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_collected ON articles(collected_at)")

    # 2. Media table (High-definition images, metrics, rights verification)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        media_uuid TEXT UNIQUE NOT NULL,
        article_id INTEGER,
        post_id INTEGER,
        original_url TEXT NOT NULL,
        local_path TEXT,
        file_format TEXT,
        width INTEGER DEFAULT 0,
        height INTEGER DEFAULT 0,
        aspect_ratio REAL DEFAULT 0.0,
        file_size_bytes INTEGER DEFAULT 0,
        sharpness_score REAL DEFAULT 0.0,
        sha256 TEXT,
        phash TEXT,
        quality_status TEXT DEFAULT 'UNVERIFIED',
        rights_status TEXT DEFAULT 'WAITING_FOR_RIGHTS',
        rights_source TEXT,
        author_owner TEXT,
        license_type TEXT,
        credit_required TEXT,
        created_at TEXT,
        FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE SET NULL,
        FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE SET NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_sha256 ON media(sha256)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_phash ON media(phash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_quality ON media(quality_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_rights ON media(rights_status)")

    # 3. Posts table (Editorial drafts, scheduling & Facebook publishing)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_uuid TEXT UNIQUE NOT NULL,
        article_id INTEGER,
        post_type TEXT DEFAULT 'ORIGINAL_PHOTO_POST',
        category TEXT NOT NULL,
        caption TEXT NOT NULL,
        hashtags TEXT,
        credit_source TEXT,
        status TEXT DEFAULT 'DRAFT',
        operating_mode TEXT DEFAULT 'SHADOW_MODE',
        target_slot TEXT,
        scheduled_time TEXT,
        published_time TEXT,
        fb_post_id TEXT,
        fb_permalink TEXT,
        error_message TEXT,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE SET NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_scheduled ON posts(scheduled_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category)")

    # 4. Sources table (Source registry with reliability & health tracking)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        feed_url TEXT,
        country TEXT NOT NULL,
        language TEXT NOT NULL,
        default_category TEXT NOT NULL,
        reliability_score REAL DEFAULT 0.8,
        rate_limit_seconds INTEGER DEFAULT 60,
        is_active BOOLEAN DEFAULT 1,
        last_checked_at TEXT,
        last_status TEXT DEFAULT 'INITIAL',
        created_at TEXT
    )
    """)

    # 5. System Settings table (Key-value store for modes, mixes, secrets)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT
    )
    """)

    # 6. Audit Logs table (Security, emergency stop, action audits)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        module TEXT NOT NULL,
        details TEXT,
        created_at TEXT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at)")

    conn.commit()

    # Seed Default Settings if not present
    now_iso = datetime.now().isoformat()
    default_settings = [
        ("operating_mode", DEFAULT_OPERATING_MODE),
        ("emergency_stop", "false"),
        ("content_mix", json.dumps(DEFAULT_CONTENT_MIX, ensure_ascii=False)),
        ("meta_page_id", ""),
        ("meta_page_access_token", ""),
        ("gemini_api_key", ""),
        ("ollama_host", "http://localhost:11434"),
        ("ollama_model", "qwen2.5"),
    ]
    for k, v in default_settings:
        cursor.execute("INSERT OR IGNORE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)", (k, v, now_iso))

    # Sync Cloud Environment Secrets into system_settings when provided
    env_secret_map = {
        "META_PAGE_ID": "meta_page_id",
        "META_PAGE_ACCESS_TOKEN": "meta_page_access_token",
        "META_APP_ID": "meta_app_id",
        "META_APP_SECRET": "meta_app_secret",
        "GEMINI_API_KEY": "gemini_api_key",
        "OPERATING_MODE": "operating_mode",
    }
    for env_key, setting_key in env_secret_map.items():
        env_val = os.getenv(env_key, "").strip()
        if env_val:
            cursor.execute(
                "INSERT INTO system_settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (setting_key, env_val, now_iso)
            )
            if setting_key == "meta_page_access_token":
                cursor.execute(
                    "INSERT INTO system_settings (key, value, updated_at) VALUES ('meta_effective_page_token', ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                    (env_val, now_iso)
                )

    conn.commit()
    conn.close()

def log_audit(action: str, module: str, details: str = "") -> None:
    """Helper to record audit logs."""
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO audit_logs (action, module, details, created_at) VALUES (?, ?, ?, ?)",
            (action, module, details, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging audit: {e}")

def get_setting(key: str, default: str = "") -> str:
    """Get system setting by key."""
    conn = get_db_connection()
    row = conn.execute("SELECT value FROM system_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str) -> None:
    """Set system setting by key."""
    conn = get_db_connection()
    now_iso = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO system_settings (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value, now_iso)
    )
    conn.commit()
    conn.close()
    log_audit("SETTING_UPDATE", "SETTINGS", f"Updated setting {key}")
