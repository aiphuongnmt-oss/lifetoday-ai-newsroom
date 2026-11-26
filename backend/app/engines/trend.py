"""
LIFE TODAY — AI NEWSROOM V1.0
Trend Engine: 6-factor Objective Editorial Scoring
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple
import json

def calculate_freshness_score(published_at: str) -> float:
    """Calculate freshness score (max 20 pts)."""
    if not published_at:
        return 10.0
    try:
        # Normalize ISO or RFC formats
        pub_dt = None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                pub_dt = datetime.strptime(published_at[:19], fmt)
                break
            except ValueError:
                continue

        if not pub_dt:
            return 10.0

        diff_hours = (datetime.now() - pub_dt).total_seconds() / 3600.0
        if diff_hours < 0:
            diff_hours = 0.0

        if diff_hours <= 1.0:
            return 20.0
        elif diff_hours <= 3.0:
            return 16.0
        elif diff_hours <= 6.0:
            return 12.0
        elif diff_hours <= 12.0:
            return 8.0
        elif diff_hours <= 24.0:
            return 4.0
        else:
            return 1.0
    except Exception:
        return 8.0

def calculate_interest_score(title: str, summary: str, source_tier: float) -> float:
    """Calculate interest score based on keywords and tier (max 20 pts)."""
    score = source_tier * 10.0 # 8 - 10 pts
    text = (title + " " + (summary or "")).lower()

    high_interest_keywords = [
        "chính thức", "bộ ảnh", "thảm đỏ", "ra mắt", "comeback", "oscar",
        "cannes", "fashion week", "met gala", "concert", "tour", "album",
        "trailer", "bom tấn", "đại sứ", "ambassador", "lookbook", "bảng xếp hạng",
        "billboard", "grammy", "emmy", "thắng lớn", "phá kỷ lục", "kỷ lục"
    ]

    matches = sum(1 for kw in high_interest_keywords if kw in text)
    score += min(matches * 2.5, 10.0)
    return min(round(score, 1), 20.0)

def calculate_reliability_score(source_reliability: float) -> float:
    """Calculate reliability score (max 25 pts)."""
    return round(source_reliability * 25.0, 1)

def calculate_viral_potential(has_media: bool, title: str) -> float:
    """Calculate viral potential (max 15 pts)."""
    score = 8.0 if has_media else 2.0
    if any(k in title.lower() for k in ["bộ ảnh", "hình ảnh", "tạo hình", "nhan sắc", "thời trang", "đẹp nhất", "ấn tượng"]):
        score += 5.0
    return min(round(score, 1), 15.0)

def calculate_fit_score(category: str) -> float:
    """Calculate Life Today brand alignment score (max 10 pts)."""
    fit_weights = {
        "Showbiz": 10.0,
        "Thời trang và làm đẹp": 10.0,
        "Du lịch": 10.0,
        "Phim ảnh": 9.5,
        "Âm nhạc": 9.0,
        "Trending": 8.5,
        "Ẩm thực": 8.0,
        "Văn hóa và nghệ thuật": 8.0,
    }
    return fit_weights.get(category, 5.0)

def calculate_novelty_score(is_duplicate_candidate: bool = False) -> float:
    """Calculate novelty score (max 10 pts)."""
    return 2.0 if is_duplicate_candidate else 10.0

def score_article(
    title: str,
    summary: str,
    category: str,
    published_at: str,
    source_reliability: float,
    has_media: bool = False,
    is_duplicate: bool = False
) -> Tuple[float, Dict[str, float]]:
    """Compute overall trend score and itemized breakdown."""
    freshness = calculate_freshness_score(published_at)
    interest = calculate_interest_score(title, summary, source_reliability)
    reliability = calculate_reliability_score(source_reliability)
    viral = calculate_viral_potential(has_media, title)
    fit = calculate_fit_score(category)
    novelty = calculate_novelty_score(is_duplicate)

    total = round(freshness + interest + reliability + viral + fit + novelty, 1)
    breakdown = {
        "freshness": freshness,
        "interest": interest,
        "reliability": reliability,
        "viral": viral,
        "fit": fit,
        "novelty": novelty,
        "total": total
    }
    return total, breakdown
