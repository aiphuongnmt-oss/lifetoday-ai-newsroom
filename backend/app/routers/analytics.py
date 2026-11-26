"""
Router: Analytics & Content Mix Tracking (7-day / 30-day)
"""
import json
from fastapi import APIRouter
from typing import Dict, List
from backend.app.database import get_db_connection, get_setting

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/mix")
def get_content_mix_analytics():
    """
    Compute actual content mix distribution for 7-day and 30-day windows
    and compare against target mix ratios.
    """
    conn = get_db_connection()
    target_mix_raw = get_setting("content_mix", "{}")
    try:
        targets = json.loads(target_mix_raw)
    except Exception:
        targets = {}

    def get_stats_for_days(days: int):
        rows = conn.execute(
            "SELECT category, COUNT(*) as count FROM posts "
            "WHERE status IN ('PUBLISHED', 'SHADOW_PUBLISHED', 'APPROVED', 'SCHEDULED') "
            "AND created_at >= datetime('now', ? || ' days') "
            "GROUP BY category",
            (f"-{days}",)
        ).fetchall()
        total = sum(r["count"] for r in rows)
        counts = {r["category"]: r["count"] for r in rows}
        ratios = {k: round(v / max(total, 1), 3) for k, v in counts.items()}
        return {"total_posts": total, "counts": counts, "ratios": ratios}

    mix_7d = get_stats_for_days(7)
    mix_30d = get_stats_for_days(30)
    conn.close()

    return {
        "targets": targets,
        "window_7d": mix_7d,
        "window_30d": mix_30d
    }

@router.get("/logs")
def get_audit_logs(limit: int = 100):
    """Retrieve recent system audit logs."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
