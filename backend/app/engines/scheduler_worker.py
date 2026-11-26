"""
LIFE TODAY — AI NEWSROOM V1.0
Continuous Autonomous Daemon: Auto-Scheduler & Periodic News Hunter
"""
import asyncio
from datetime import datetime, timezone, timedelta
from backend.app.database import get_db_connection, get_setting, log_audit
from backend.app.engines.facebook_publisher import FacebookPublisher
from backend.app.engines.automation_worker import run_autonomous_cycle

VN_TZ = timezone(timedelta(hours=7))

async def run_scheduler_tick():
    """Check for any scheduled posts that have reached their target time."""
    now_vn = datetime.now(VN_TZ).isoformat()
    operating_mode = get_setting("operating_mode", "SHADOW_MODE")
    emergency_stop = get_setting("emergency_stop", "false").lower() == "true"

    if emergency_stop:
        return

    conn = get_db_connection()
    # Find posts scheduled for now or in the past that are still marked SCHEDULED
    due_posts = conn.execute("""
        SELECT id, scheduled_time, caption FROM posts
        WHERE status = 'SCHEDULED' AND scheduled_time <= ?
        ORDER BY scheduled_time ASC LIMIT 5
    """, (now_vn,)).fetchall()
    conn.close()

    if not due_posts:
        return

    pub = FacebookPublisher()
    for p in due_posts:
        print(f"[{datetime.now(VN_TZ).strftime('%H:%M:%S')}] Auto-publishing due post #{p['id']}...")
        res = await pub.publish_or_schedule_post(p["id"], operating_mode=operating_mode, emergency_stop=emergency_stop)
        print(f" -> Result: {res}")

async def start_autonomous_daemon():
    """Main continuous daemon loop."""
    print("=" * 65)
    print("   LIFE TODAY — CONTINUOUS AUTONOMOUS NEWSROOM DAEMON")
    print("   Running background scheduler ticks and hunting cycles...")
    print("=" * 65)

    last_hunt_hour = -1

    # On fresh Cloud boot (empty articles DB), run an initial news scan automatically
    try:
        conn_init = get_db_connection()
        art_cnt = conn_init.execute("SELECT COUNT(*) as c FROM articles").fetchone()["c"]
        conn_init.close()
        if art_cnt == 0:
            from backend.app.engines.hunter import run_news_hunter
            print("[Startup] Empty article store detected — running initial Vietnamese news scan...")
            await run_news_hunter()
    except Exception as init_err:
        print(f"Initial startup hunt error: {init_err}")

    while True:
        try:
            now_vn = datetime.now(VN_TZ)

            # 1. Check due scheduled posts every minute
            await run_scheduler_tick()

            # 2. Trigger hunting cycles at 06:30, 11:00, 17:00
            if now_vn.hour in (6, 11, 17) and now_vn.minute >= 30 and last_hunt_hour != now_vn.hour:
                print(f"\n[{now_vn.strftime('%H:%M:%S')}] Triggering scheduled hunting cycle...")
                await run_autonomous_cycle()
                last_hunt_hour = now_vn.hour

            # 3. Trigger daily storage cleanup at 03:00 AM (removes raw news > 24h & published local media)
            if now_vn.hour == 3 and now_vn.minute == 0:
                from backend.app.engines.storage_cleaner import run_storage_cleanup
                run_storage_cleanup(max_raw_article_age_hours=24)

        except Exception as e:
            print(f"Daemon tick error: {e}")

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(start_autonomous_daemon())
