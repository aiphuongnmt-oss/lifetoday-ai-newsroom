"""
LIFE TODAY — AI NEWSROOM V1.0
Comprehensive End-to-End Test Suite
"""
import asyncio
import io
from PIL import Image, ImageDraw

from backend.app.database import init_db, get_db_connection, get_setting, set_setting
from backend.app.engines.source_registry import seed_source_registry, get_all_sources
from backend.app.engines.hard_block import evaluate_hard_block
from backend.app.engines.fact_checker import verify_facts_and_compliance
from backend.app.engines.caption_engine import generate_caption_ai
from backend.app.engines.media_engine import validate_image_bytes
from backend.app.engines.media_rights import check_media_publishable, update_media_rights
from backend.app.engines.deduplication import check_duplicate_article
from backend.app.engines.scheduler import schedule_post_to_slot, get_next_available_slot
from backend.app.engines.facebook_publisher import FacebookPublisher
from backend.app.engines.automation_worker import run_pipeline_for_article

async def run_e2e_suite():
    print("=" * 60)
    print("STARTING LIFE TODAY AI NEWSROOM END-TO-END VERIFICATION")
    print("=" * 60)

    # 1. Database & Seeding
    init_db()
    conn = get_db_connection()
    conn.execute("DELETE FROM articles WHERE url LIKE '%example.com%'")
    conn.execute("DELETE FROM posts WHERE post_uuid LIKE '%e2e%' OR post_uuid LIKE '%test%'")
    conn.commit()
    conn.close()
    seed_source_registry()
    sources = get_all_sources()
    assert len(sources) >= 10, "Sources must be seeded"
    print(f"[PASSED] Step 1: Database initialized & {len(sources)} sources seeded.")

    # 2. Hard Block Evaluation
    blocked_test = "Vụ án mạng kinh hoàng và bê bối chính trị"
    is_blocked, reason, _ = evaluate_hard_block(blocked_test)
    assert is_blocked, "Must block murder & politics"
    print(f"[PASSED] Step 2: Hard Block safely intercepted forbidden topic: '{reason}'")

    # 3. Fact Checking & Ambassador hierarchy
    title = "Địch Lệ Nhiệt Ba tham dự sự kiện Dior với tư cách Đại sứ toàn cầu (Global Ambassador)"
    summary = "Nữ diễn viên xuất hiện trong trang phục mới nhất của nhà mốt Pháp."
    status, meta = verify_facts_and_compliance(title, summary, source_reliability=0.95)
    assert status == "VERIFIED", "Valid brand ambassadorship must be verified"
    assert "Dior" in meta["entities"]["brands"]
    print(f"[PASSED] Step 3: Fact Checker verified Dior Global Ambassador.")

    # 4. Media Quality Validation with Pillow
    img = Image.new("RGB", (1920, 1080), color=(20, 25, 40))
    d = ImageDraw.Draw(img)
    d.rectangle([100, 100, 1820, 980], outline=(244, 63, 94), width=10)
    d.text((500, 500), "LIFE TODAY HIGH DEFINITION TEST", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    img_bytes = buf.getvalue()

    metrics = validate_image_bytes(img_bytes)
    assert metrics["is_valid"]
    assert metrics["quality_status"] == "QUALIFIED"
    print(f"[PASSED] Step 4: Pillow validated 1920x1080 HD image (Sharpness: {metrics['sharpness_score']}) -> QUALIFIED.")

    # 5. Media Rights Clearance
    unverified_media = {"quality_status": "QUALIFIED", "rights_status": "WAITING_FOR_RIGHTS"}
    publishable, r_msg = check_media_publishable(unverified_media)
    assert not publishable, "WAITING_FOR_RIGHTS must be blocked"
    print(f"[PASSED] Step 5: Media Rights Engine blocked unverified photo: '{r_msg}'")

    # 6. Deduplication Engine
    t1 = "Lisa (BLACKPINK) phát hành album solo mới"
    t2 = "Thành viên Lisa (BLACKPINK) chính thức ra mắt album solo mới"
    conn = get_db_connection()
    # Insert dummy article
    conn.execute("""
        INSERT OR IGNORE INTO articles (guid, title, url, canonical_url, category, status, collected_at, created_at)
        VALUES ('guid_test_lisa', ?, 'https://example.com/lisa-1', 'https://example.com/lisa-1', 'Âm nhạc', 'NEW', datetime('now'), datetime('now'))
    """, (t1,))
    conn.commit()
    conn.close()

    is_dup, dup_reason = check_duplicate_article("https://example.com/lisa-2", t2)
    assert is_dup, "Near duplicate headline must be detected"
    print(f"[PASSED] Step 6: Deduplication intercepted duplicate news: '{dup_reason}'")

    # 7. AI Caption Synthesis
    cap_res = await generate_caption_ai(
        title="Rosé xuất hiện lộng lẫy tại sự kiện thời trang Paris",
        summary="Nữ ca sĩ gây sốt với phong cách sang trọng và thần thái cuốn hút.",
        category="Thời trang và làm đẹp",
        credit_source="Official Press Kit"
    )
    assert "#LifeToday" in cap_res["hashtags"]
    assert len(cap_res["caption"].split()) <= 60
    print(f"[PASSED] Step 7: Caption Engine generated concise aesthetic caption ({cap_res['word_count']} words, Engine: {cap_res['engine_used']}).")

    # 8. Full Pipeline & Scheduling to Slot
    conn = get_db_connection()
    import time
    ts = int(time.time())
    test_guid = f"guid_e2e_{ts}"
    unique_title = f"Mỹ Tâm công bố đêm nhạc đặc biệt tại Đà Lạt {ts}"
    cursor = conn.execute("""
        INSERT INTO articles (guid, title, summary, url, canonical_url, category, status, trend_score, collected_at, created_at)
        VALUES (?, ?, 'Nữ ca sĩ mang đến những bản phối đặc sắc.', ?, ?, 'Âm nhạc', 'NEW', 88.5, datetime('now'), datetime('now'))
    """, (test_guid, unique_title, f"https://example.com/mytam-{ts}", f"https://example.com/mytam-{ts}"))
    art_id = cursor.lastrowid
    conn.commit()
    conn.close()

    pipe_res = await run_pipeline_for_article(art_id)
    assert pipe_res["success"], f"Pipeline failed: {pipe_res}"
    post_id = pipe_res["post_id"]
    print(f"[PASSED] Step 8: Pipeline processed article #{art_id} -> Post #{post_id} (Slot: {pipe_res['scheduling']['slot']}).")

    # 9. Shadow Mode Publishing & Verification
    pub = FacebookPublisher()
    pub_res = await pub.publish_or_schedule_post(post_id, operating_mode="SHADOW_MODE")
    assert pub_res["success"]
    assert pub_res["shadow_mode"]
    assert "shadow_fb_" in pub_res["fb_post_id"]
    print(f"[PASSED] Step 9: Shadow Publishing verified Post ID {pub_res['fb_post_id']} -> {pub_res['fb_permalink']}.")

    # 10. Emergency Stop Safety Brake
    set_setting("emergency_stop", "true")
    stop_res = await pub.publish_or_schedule_post(post_id, operating_mode="SHADOW_MODE", emergency_stop=True)
    assert not stop_res["success"]
    assert "EMERGENCY_STOP" in stop_res["error"]
    set_setting("emergency_stop", "false") # Restore
    print(f"[PASSED] Step 10: Emergency Stop safety brake successfully halted publication.")

    print("=" * 60)
    print("ALL 10 END-TO-END VERIFICATION CRITERIA PASSED 100%!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_e2e_suite())
