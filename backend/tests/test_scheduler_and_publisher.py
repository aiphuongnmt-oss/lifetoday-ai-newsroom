"""
Test Facebook Publisher, Smart Scheduler & Pipeline Worker
"""
import asyncio
from backend.app.database import init_db, get_db_connection
from backend.app.engines.scheduler import get_next_available_slot, schedule_post_to_slot
from backend.app.engines.facebook_publisher import FacebookPublisher
from backend.app.engines.automation_worker import run_pipeline_for_article

async def test_scheduler():
    init_db()
    slot_name, scheduled_iso = get_next_available_slot("Thời trang và làm đẹp")
    print(f"Next available slot: {slot_name} at {scheduled_iso}")
    assert slot_name in ["07:30", "10:00", "12:00", "15:00", "18:00", "20:30", "CUSTOM"], "Valid slot"
    print("Scheduler Tests PASSED!")

async def test_shadow_publishing():
    # Insert a dummy post for shadow mode test
    conn = get_db_connection()
    cursor = conn.execute("""
        INSERT INTO posts (
            post_uuid, category, caption, hashtags, status, operating_mode, created_at, updated_at
        ) VALUES ('uuid_test_123', 'Showbiz', 'Test Caption for Life Today', '#LifeToday', 'APPROVED', 'SHADOW_MODE', datetime('now'), datetime('now'))
    """)
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()

    pub = FacebookPublisher()
    res = await pub.publish_or_schedule_post(post_id, operating_mode="SHADOW_MODE")
    print(f"Shadow Publishing Result: {res}")
    assert res["success"], "Shadow publishing should succeed"
    assert res["shadow_mode"], "Must be shadow mode"
    assert "shadow_fb_" in res["fb_post_id"], "Should generate shadow Post ID"
    print("Shadow Publisher Tests PASSED!")

if __name__ == "__main__":
    asyncio.run(test_scheduler())
    asyncio.run(test_shadow_publishing())
