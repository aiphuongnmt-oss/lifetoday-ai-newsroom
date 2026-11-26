"""
LIFE TODAY — AI NEWSROOM V1.0
Smart Scheduler Engine: Peak Engagement Slot Allocation & Frequency Capping
"""
from datetime import datetime, date, time, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from backend.app.config import DEFAULT_PUBLISH_SLOTS, MAX_POSTS_PER_DAY
from backend.app.database import get_db_connection, log_audit

VN_TZ = timezone(timedelta(hours=7))

# Mapping categories to optimal engagement slots
SLOT_CATEGORY_AFFINITY = {
    "07:30": ["Du lịch", "Trending", "Ẩm thực"],
    "10:00": ["Showbiz", "Thời trang và làm đẹp"],
    "12:00": ["Âm nhạc", "Showbiz", "Trending"],
    "15:00": ["Thời trang và làm đẹp", "Văn hóa và nghệ thuật"],
    "18:00": ["Phim ảnh", "Showbiz"],
    "20:30": ["Phim ảnh", "Thời trang và làm đẹp", "Âm nhạc"]
}

def get_next_available_slot(category: str = "Showbiz") -> Tuple[str, str]:
    """
    Find the next available scheduling slot (Asia/Ho_Chi_Minh).
    Returns (slot_name: str, scheduled_iso: str).
    """
    now_vn = datetime.now(VN_TZ)
    conn = get_db_connection()

    # Search today and next 3 days
    for day_offset in range(4):
        target_date = (now_vn + timedelta(days=day_offset)).date()

        # Count scheduled posts for this date
        date_str = target_date.isoformat()
        count_row = conn.execute(
            "SELECT COUNT(*) as count FROM posts WHERE scheduled_time LIKE ? AND status IN ('SCHEDULED', 'PUBLISHED', 'SHADOW_PUBLISHED')",
            (f"{date_str}%",)
        ).fetchone()
        if count_row["count"] >= MAX_POSTS_PER_DAY:
            continue

        for slot_str in DEFAULT_PUBLISH_SLOTS:
            slot_h, slot_m = map(int, slot_str.split(":"))
            slot_dt = datetime.combine(target_date, time(slot_h, slot_m, tzinfo=VN_TZ))

            # Must be at least 20 minutes in future
            if slot_dt < now_vn + timedelta(minutes=20):
                continue

            # Check if this exact slot is already booked
            slot_iso_prefix = slot_dt.strftime("%Y-%m-%dT%H:%M")
            existing = conn.execute(
                "SELECT id FROM posts WHERE scheduled_time LIKE ? AND status IN ('SCHEDULED', 'PUBLISHED', 'SHADOW_PUBLISHED')",
                (f"{slot_iso_prefix}%",)
            ).fetchone()

            if not existing:
                conn.close()
                return slot_str, slot_dt.isoformat()

    conn.close()
    # Fallback to tomorrow 10:00
    fallback = (now_vn + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    return "10:00", fallback.isoformat()

def schedule_post_to_slot(post_id: int, custom_time: Optional[str] = None) -> Dict:
    """Assign post to next available slot or specified time."""
    conn = get_db_connection()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        return {"success": False, "error": "Post not found"}

    if custom_time:
        slot_name = "CUSTOM"
        scheduled_iso = custom_time
    else:
        slot_name, scheduled_iso = get_next_available_slot(post["category"])

    now_iso = datetime.now(VN_TZ).isoformat()
    conn.execute("""
        UPDATE posts SET
            target_slot = ?,
            scheduled_time = ?,
            status = 'SCHEDULED',
            updated_at = ?
        WHERE id = ?
    """, (slot_name, scheduled_iso, now_iso, post_id))
    conn.commit()
    conn.close()

    log_audit("POST_SCHEDULED", "SCHEDULER", f"Post #{post_id} scheduled for {slot_name} at {scheduled_iso}")
    return {
        "success": True,
        "post_id": post_id,
        "slot": slot_name,
        "scheduled_time": scheduled_iso
    }
