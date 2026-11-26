"""
Test Trend Engine Scoring
"""
from datetime import datetime, timezone, timedelta
from backend.app.engines.trend import score_article

def test_trend():
    now_iso = datetime.now(timezone(timedelta(hours=7))).isoformat()
    score, breakdown = score_article(
        title="Địch Lệ Nhiệt Ba xuất hiện lộng lẫy tại thảm đỏ Cannes, bộ ảnh chính thức gây sốt",
        summary="Nữ diễn viên trở thành tâm điểm với trang phục Haute Couture mới nhất.",
        category="Thời trang và làm đẹp",
        published_at=now_iso,
        source_reliability=0.95,
        has_media=True,
        is_duplicate=False
    )
    print(f"Computed Score: {score}/100")
    print(f"Breakdown: {breakdown}")
    assert score >= 70.0, "High-profile fashion event should score high"
    print("Trend Engine Verification PASSED!")

if __name__ == "__main__":
    test_trend()
