"""
LIFE TODAY — AI NEWSROOM V1.0
News Hunter Engine: Autonomous Harvester & Multi-source Ingest
"""
import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import feedparser
import html
import httpx
from bs4 import BeautifulSoup

from backend.app.config import TIMEZONE
from backend.app.database import get_db_connection, log_audit
from backend.app.engines.source_registry import get_all_sources
from backend.app.engines.trend import score_article
from backend.app.engines.hard_block import evaluate_hard_block

VN_TZ = timezone(timedelta(hours=7))

def clean_canonical_url(url: str) -> str:
    """Strip tracking queries (utm_*, ref, fbadid, fbclid) to get canonical URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        clean_query = []
        for k, v in parse_qs(parsed.query).items():
            if not k.startswith("utm_") and k not in ("fbclid", "ref", "source", "fbadid"):
                for val in v:
                    clean_query.append((k, val))
        new_query = urlencode(clean_query)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))
    except Exception:
        return url

def generate_article_guid(url: str, title: str) -> str:
    """Generate SHA-256 GUID for canonical deduplication."""
    clean = clean_canonical_url(url)
    raw = f"{clean.strip().lower()}|{title.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def clean_html(text: str) -> str:
    """Strip HTML tags, unescape entities, and clean whitespace."""
    if not text:
        return ""
    unescaped = html.unescape(text)
    soup = BeautifulSoup(unescaped, "html.parser")
    clean = soup.get_text(separator=" ").strip()
    return re.sub(r"\s+", " ", clean)

def extract_media_from_entry(entry: dict) -> List[str]:
    """Extract HD image URLs from enclosures, media_content, or description HTML."""
    image_urls = []
    # 1. Enclosures
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image/") and enc.get("href"):
            image_urls.append(enc["href"])

    # 2. Media content
    for media in entry.get("media_content", []):
        if media.get("url"):
            image_urls.append(media["url"])

    # 3. Media thumbnail (fallback)
    for thumb in entry.get("media_thumbnail", []):
        if thumb.get("url"):
            image_urls.append(thumb["url"])

    # 4. Parse description HTML for images
    summary = entry.get("summary", "") or entry.get("description", "")
    if summary and "<img" in summary:
        soup = BeautifulSoup(summary, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and not src.endswith(".gif") and ("1x1" not in src):
                image_urls.append(src)

    # Filter unique URLs
    seen = set()
    unique_urls = []
    for u in image_urls:
        if u and u not in seen:
            seen.add(u)
            unique_urls.append(u)
    return unique_urls

def parse_published_time(entry: dict) -> str:
    """Parse feed entry published time to standard ISO format."""
    now_iso = datetime.now(VN_TZ).isoformat()
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(VN_TZ)
            return dt.isoformat()
        except Exception:
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).astimezone(VN_TZ)
            return dt.isoformat()
        except Exception:
            pass
    return now_iso

async def fetch_feed(source: dict) -> List[dict]:
    """Fetch and parse feed from a registered source."""
    feed_url = source.get("feed_url") or source.get("url")
    if not feed_url:
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 LifeTodayNewsBot/1.0"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(feed_url)
            if resp.status_code != 200:
                return []
            feed_content = resp.text
            parsed = feedparser.parse(feed_content)
            return parsed.entries
    except Exception as e:
        print(f"Error fetching feed {source['id']}: {e}")
        return []

def _has_keyword(text: str, keywords: List[str]) -> bool:
    """Word-boundary aware keyword matching to prevent Vietnamese substring false positives."""
    for kw in keywords:
        pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
        if re.search(pattern, text):
            return True
    return False

def refine_category(title: str, summary: str = "", default_category: str = "Showbiz") -> str:
    """
    Intelligently refine category based on title & content keywords,
    while respecting specialized source domains (Thời trang, Du lịch, Ẩm thực).
    """
    title_l = (title or "").lower()
    full_l = f"{title_l} {(summary or '').lower()}"

    # 1. Specialized Fashion sources stay Fashion (avoid stealing dresses for singers into Music)
    if default_category == "Thời trang và làm đẹp":
        return "Thời trang và làm đẹp"

    # 2. Specialized Travel / Food sources: only distinguish between Travel, Food, and Festival/Music events
    food_keywords = [
        "ẩm thực", "món ngon", "nhà hàng", "quán ăn", "đặc sản", "cà phê", "nấu ăn", "thực đơn",
        "mỹ vị", "bếp trưởng", "đầu bếp", "món ăn", "bún", "phở", "bánh xèo", "lẩu", "pizza",
        "trà đá", "bánh khoái", "bánh trôi", "quán bún", "cừu nướng", "ăn no", "sản vật"
    ]
    travel_keywords = [
        "du lịch", "check-in", "check in", "khách sạn", "resort", "điểm đến", "hành trình", "tour",
        "trekking", "biển mây", "sân bay", "tàu du lịch", "ngôi làng", "làng cổ", "chợ giáng sinh",
        "thắng cảnh", "cáp treo", "đà lạt", "tà xùa"
    ]
    if default_category in ("Du lịch", "Ẩm thực"):
        if _has_keyword(title_l, food_keywords):
            return "Ẩm thực"
        if _has_keyword(title_l, travel_keywords):
            return "Du lịch"
        return default_category

    # 3. General Entertainment / Showbiz sources: accurately split into Music, Film, Fashion, Culture, Showbiz
    fashion_keywords = [
        "thời trang", "bộ sưu tập", "tuần lễ thời trang", "fashion", "outfit", "lên đồ", "thảm đỏ",
        "lookbook", "trang phục", "váy", "diện đầm", "hoa hậu", "á hậu", "miss universe",
        "miss international", "stylist", "làm đẹp", "makeup", "son môi", "trang sức"
    ]
    music_keywords = [
        "album", "mv", "ca khúc", "bài hát", "ca sĩ", "nhạc sĩ", "nhạc hội", "đại nhạc hội",
        "concert", "liveshow", "vpop", "kpop", "grammy", "single", "bản hit", "giai điệu",
        "âm nhạc", "nhạc việt", "say hi", "anh trai", "chị đẹp", "da lab", "bolero",
        "rapper", "ban nhạc", "đêm nhạc", "soundtrack", "biểu diễn tại"
    ]
    film_keywords = [
        "phim", "diễn viên", "đạo diễn", "chiếu rạp", "bom tấn", "trailer", "màn ảnh", "vai diễn",
        "điện ảnh", "series", "bộ phim", "tập phim", "oscar", "cannes", "rồng xanh", "phim trường",
        "anime", "liên hoan phim", "avatar", "đóng cặp"
    ]
    culture_keywords = [
        "văn hóa", "di sản", "triển lãm", "bảo tàng", "nghệ thuật", "thành cổ", "di tích",
        "trùng tu", "hội họa", "kiến trúc cổ", "dân gian"
    ]

    # Check TITLE first (highest precision!)
    if _has_keyword(title_l, music_keywords):
        return "Âm nhạc"
    if _has_keyword(title_l, film_keywords):
        return "Phim ảnh"
    if _has_keyword(title_l, fashion_keywords):
        return "Thời trang và làm đẹp"
    if _has_keyword(title_l, culture_keywords):
        return "Văn hóa và nghệ thuật"

    # Secondary check on full text (title + summary)
    if _has_keyword(full_l, music_keywords):
        return "Âm nhạc"
    if _has_keyword(full_l, film_keywords):
        return "Phim ảnh"
    if _has_keyword(full_l, fashion_keywords):
        return "Thời trang và làm đẹp"
    if _has_keyword(full_l, culture_keywords):
        return "Văn hóa và nghệ thuật"

    return default_category

async def hunt_source(source: dict, category_filter: Optional[str] = None) -> List[Dict]:
    """Hunt news articles from a specific source (capped to Top 5 freshest per feed)."""
    raw_entries = await fetch_feed(source)
    entries = raw_entries[:8]  # Only process the top freshest entries per source
    new_articles = []
    conn = get_db_connection()
    now_vn = datetime.now(VN_TZ).isoformat()

    for entry in entries:
        raw_title = html.unescape(entry.get("title", "").strip())
        link = entry.get("link", "").strip()
        if not raw_title or not link:
            continue

        # Localize foreign title if needed
        if source.get("language") != "vi":
            from backend.app.engines.translator import translate_headline_rule_based
            vi_t = translate_headline_rule_based(raw_title)
            title = f"[Dịch] {vi_t}" if vi_t != raw_title else f"[Quốc tế] {raw_title}"
        else:
            title = raw_title

        canonical_url = clean_canonical_url(link)
        guid = generate_article_guid(canonical_url, title)

        # Check existing
        existing = conn.execute("SELECT id FROM articles WHERE guid = ? OR canonical_url = ?", (guid, canonical_url)).fetchone()
        if existing:
            continue

        raw_summary = entry.get("summary", "") or entry.get("description", "")
        clean_summary_text = clean_html(raw_summary)

        # STRICT HARD BLOCK FILTER: Brand safety check (Zero tolerance for politics, crime, death, lawsuits, accidents)
        is_blocked, block_reason, _ = evaluate_hard_block(title, clean_summary_text)
        if is_blocked:
            continue  # Discard negative, sensitive, or political news immediately at harvest

        published_at = parse_published_time(entry)

        # STRICT 24-HOUR FILTER: Skip any news published older than 24 hours
        try:
            pub_dt = datetime.fromisoformat(published_at)
            age_hours = (datetime.now(VN_TZ) - pub_dt).total_seconds() / 3600.0
            if age_hours > 24.0:
                continue # Discard news older than 24 hours immediately
        except Exception:
            pass

        media_urls = extract_media_from_entry(entry)

        assigned_category = refine_category(title, clean_summary_text, source.get("default_category", "Showbiz"))
        if category_filter and category_filter != "Trending" and category_filter != assigned_category:
            continue

        # Score with Trend Engine
        score, breakdown = score_article(
            title=title,
            summary=clean_summary_text,
            category=assigned_category,
            published_at=published_at,
            source_reliability=source.get("reliability_score", 0.8),
            has_media=len(media_urls) > 0,
            is_duplicate=False
        )

        raw_meta = {
            "source_id": source["id"],
            "raw_media_urls": media_urls,
            "tags": [t.get("term", "") for t in entry.get("tags", [])] if entry.get("tags") else []
        }

        try:
            cursor = conn.execute("""
                INSERT INTO articles (
                    guid, title, summary, content, url, canonical_url, source_id,
                    source_name, country, language, category, published_at, collected_at,
                    trend_score, trend_breakdown, status, raw_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW', ?, ?)
            """, (
                guid, title, clean_summary_text, clean_summary_text, link, canonical_url,
                source["id"], source["name"], source["country"], source["language"],
                assigned_category, published_at, now_vn, score,
                json.dumps(breakdown), json.dumps(raw_meta), now_vn
            ))
            article_id = cursor.lastrowid

            # Save extracted raw media URLs to media table with WAITING_FOR_RIGHTS
            for img_url in media_urls:
                media_uuid = hashlib.sha256(f"{article_id}|{img_url}".encode()).hexdigest()
                conn.execute("""
                    INSERT OR IGNORE INTO media (
                        media_uuid, article_id, original_url, quality_status,
                        rights_status, rights_source, created_at
                    ) VALUES (?, ?, ?, 'UNVERIFIED', 'WAITING_FOR_RIGHTS', ?, ?)
                """, (media_uuid, article_id, img_url, source["name"], now_vn))

            new_articles.append({
                "id": article_id,
                "guid": guid,
                "title": title,
                "url": link,
                "category": assigned_category,
                "trend_score": score,
                "published_at": published_at,
                "media_count": len(media_urls)
            })
        except Exception as e:
            print(f"Error inserting article: {e}")

    conn.commit()
    conn.close()
    return new_articles

async def run_news_hunter(
    category: Optional[str] = None,
    country: Optional[str] = None,
    source_id: Optional[str] = None
) -> Dict:
    """Execute news scan across all registered and matching sources."""
    sources = get_all_sources(active_only=True)
    if country:
        sources = [s for s in sources if s["country"].upper() == country.upper()]
    if source_id:
        sources = [s for s in sources if s["id"] == source_id]
    ENTERTAINMENT_CATEGORIES = {"Showbiz", "Phim ảnh", "Âm nhạc", "Thời trang và làm đẹp", "Văn hóa và nghệ thuật"}
    if category and category != "Trending":
        if category in ENTERTAINMENT_CATEGORIES:
            sources = [s for s in sources if s.get("default_category") in ENTERTAINMENT_CATEGORIES]
        else:
            sources = [s for s in sources if s.get("default_category") == category]

    tasks = [hunt_source(s, category) for s in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_new_articles = []
    for r in results:
        if isinstance(r, list):
            all_new_articles.extend(r)

    log_audit("NEWS_SCAN", "NEWS_HUNTER", f"Scanned {len(sources)} sources, found {len(all_new_articles)} new articles")
    return {
        "sources_scanned": len(sources),
        "new_articles_count": len(all_new_articles),
        "articles": all_new_articles
    }
