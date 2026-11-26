"""
Test Editorial Engines: Hard Block, Fact Checker & Caption Engine
"""
import asyncio
from backend.app.engines.hard_block import evaluate_hard_block
from backend.app.engines.fact_checker import verify_facts_and_compliance
from backend.app.engines.caption_engine import generate_caption_ai

def test_hard_block():
    # Test safe showbiz news
    safe_title = "Rosé (BLACKPINK) xuất hiện thanh lịch tại sự kiện Saint Laurent Paris"
    is_blocked, reason, _ = evaluate_hard_block(safe_title)
    assert not is_blocked, f"Safe title should not be blocked: {reason}"

    # Test blocked political/conflict news
    blocked_title = "Quân sự và vũ khí chiến tranh tại biên giới"
    is_blocked, reason, cat = evaluate_hard_block(blocked_title)
    assert is_blocked, "War/political content must be blocked"
    print(f"Hard block correctly caught: {reason}")

    # Test blocked drama/scandal
    scandal_title = "Lộ tin nhắn ngoại tình chấn động của sao nam đình đám"
    is_blocked, reason, cat = evaluate_hard_block(scandal_title)
    assert is_blocked, "Scandal/drama must be blocked"
    print(f"Hard block correctly caught: {reason}")
    print("Hard Block Tests PASSED!")

def test_fact_checker():
    title = "Song Hye Kyo tham dự show thời trang Fendi với tư cách Đại sứ thương hiệu"
    summary = "Nữ diễn viên diện thiết kế mới nhất của thương hiệu Fendi tại tuần lễ thời trang."
    status, meta = verify_facts_and_compliance(title, summary, source_reliability=0.95)
    assert status == "VERIFIED", f"Expected VERIFIED, got {status}"
    print(f"Fact Check Entities: {meta['entities']}")
    print("Fact Checker Tests PASSED!")

async def test_caption():
    title = "Dua Lipa diện váy xuyên thấu trên thảm đỏ sự kiện âm nhạc tại London"
    summary = "Nữ ca sĩ gây chú ý với thần thái cuốn hút và phong cách thời trang táo bạo."
    res = await generate_caption_ai(
        title=title,
        summary=summary,
        category="Thời trang và làm đẹp",
        credit_source="Vogue UK"
    )
    print(f"Generated Caption: {res['full_post_text']}")
    print(f"Engine: {res['engine_used']} | Words: {res['word_count']}")
    assert 10 <= res['word_count'] <= 60, "Word count should adhere to standards"
    assert "#LifeToday" in res['hashtags'], "Must contain #LifeToday"
    print("Caption Engine Tests PASSED!")

if __name__ == "__main__":
    test_hard_block()
    test_fact_checker()
    asyncio.run(test_caption())
