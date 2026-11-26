"""
Router: System Settings & Emergency Stop
"""
import json
import os
import httpx
from fastapi import APIRouter
from typing import Dict, Optional
from backend.app.config import APP_NAME, APP_VERSION, DEFAULT_OPERATING_MODE
from backend.app.database import get_db_connection, get_setting, set_setting, log_audit
from backend.app.models.settings import SystemSettingsUpdate, SystemStatusOut
from backend.app.engines.facebook_publisher import FacebookPublisher

router = APIRouter(prefix="/api/settings", tags=["Settings"])

@router.get("/status")
def get_system_status():
    """Retrieve system health, mode, emergency stop, and counters."""
    conn = get_db_connection()
    articles_count = conn.execute("SELECT COUNT(*) as count FROM articles").fetchone()["count"]
    pending_posts = conn.execute("SELECT COUNT(*) as count FROM posts WHERE status IN ('PENDING_REVIEW', 'APPROVED', 'FAILED')").fetchone()["count"]
    scheduled_posts = conn.execute("SELECT COUNT(*) as count FROM posts WHERE status = 'SCHEDULED'").fetchone()["count"]
    published_posts = conn.execute("SELECT COUNT(*) as count FROM posts WHERE status IN ('PUBLISHED', 'SHADOW_PUBLISHED')").fetchone()["count"]
    media_count = conn.execute("SELECT COUNT(*) as count FROM media").fetchone()["count"]
    sources_count = conn.execute("SELECT COUNT(*) as count FROM sources WHERE is_active = 1").fetchone()["count"]
    conn.close()

    operating_mode = get_setting("operating_mode", DEFAULT_OPERATING_MODE)
    emergency_stop = get_setting("emergency_stop", "false").lower() == "true"
    content_mix_raw = get_setting("content_mix", "{}")
    try:
        content_mix = json.loads(content_mix_raw)
    except Exception:
        content_mix = {}

    pub = FacebookPublisher()
    meta_page_id = get_setting("meta_page_id")

    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "operating_mode": operating_mode,
        "emergency_stop": emergency_stop,
        "content_mix": content_mix,
        "articles_count": articles_count,
        "pending_posts_count": pending_posts,
        "scheduled_posts_count": scheduled_posts,
        "published_posts_count": published_posts,
        "media_count": media_count,
        "sources_count": sources_count,
        "meta_configured": pub.is_configured(),
        "meta_page_id": meta_page_id,
        "gemini_configured": bool(get_setting("gemini_api_key")),
        "ollama_host": get_setting("ollama_host", "http://localhost:11434")
    }

@router.post("")
def update_settings(payload: SystemSettingsUpdate):
    """Update system settings (operating mode, credentials, mix)."""
    if payload.operating_mode is not None:
        set_setting("operating_mode", payload.operating_mode)
    if payload.emergency_stop is not None:
        set_setting("emergency_stop", "true" if payload.emergency_stop else "false")
    if payload.content_mix is not None:
        set_setting("content_mix", json.dumps(payload.content_mix, ensure_ascii=False))
    if payload.meta_page_id is not None:
        set_setting("meta_page_id", payload.meta_page_id)
    if payload.meta_page_access_token is not None:
        token_to_save = payload.meta_page_access_token.strip()
        app_id = get_setting("meta_app_id") or os.getenv("META_APP_ID", "")
        app_secret = get_setting("meta_app_secret") or os.getenv("META_APP_SECRET", "")

        # Auto-exchange short-lived token to long-lived (60 days or permanent) via App Secret
        if app_id and app_secret and token_to_save:
            try:
                with httpx.Client(timeout=10.0) as client:
                    ex_res = client.get("https://graph.facebook.com/v21.0/oauth/access_token", params={
                        "grant_type": "fb_exchange_token",
                        "client_id": app_id,
                        "client_secret": app_secret,
                        "fb_exchange_token": token_to_save
                    })
                    if ex_res.status_code == 200:
                        long_lived = ex_res.json().get("access_token")
                        if long_lived:
                            token_to_save = long_lived
                            log_audit("TOKEN_AUTO_EXCHANGED", "SETTINGS", "Token upgraded to long-lived permanent via App Secret")
            except Exception as ex_err:
                log_audit("TOKEN_EXCHANGE_ERROR", "SETTINGS", str(ex_err))

        set_setting("meta_page_access_token", token_to_save)
        # Clear cached effective token to force immediate re-resolution
        conn_clear = get_db_connection()
        conn_clear.execute("DELETE FROM system_settings WHERE key = 'meta_effective_page_token'")
        conn_clear.commit()
        conn_clear.close()
    if payload.gemini_api_key is not None:
        set_setting("gemini_api_key", payload.gemini_api_key)
    if payload.ollama_host is not None:
        set_setting("ollama_host", payload.ollama_host)
    if payload.ollama_model is not None:
        set_setting("ollama_model", payload.ollama_model)

    return {"success": True, "message": "Cài đặt đã được cập nhật thành công"}

@router.post("/emergency_stop")
def toggle_emergency_stop():
    """Toggle Emergency Stop brake."""
    current = get_setting("emergency_stop", "false").lower() == "true"
    new_state = not current
    set_setting("emergency_stop", "true" if new_state else "false")
    log_audit("EMERGENCY_STOP_TOGGLED", "SYSTEM", f"Emergency Stop is now {new_state}")
    return {"emergency_stop": new_state}

@router.get("/storage")
def get_storage():
    """Retrieve disk and database usage statistics."""
    from backend.app.engines.storage_cleaner import get_storage_stats
    return get_storage_stats()

@router.post("/cleanup")
def cleanup_storage(max_age_hours: int = 24):
    """Trigger manual storage purge of old unused articles and unneeded media."""
    from backend.app.engines.storage_cleaner import run_storage_cleanup
    res = run_storage_cleanup(max_raw_article_age_hours=max_age_hours)
    return {"success": True, "details": res}
