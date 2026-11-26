"""
LIFE TODAY — AI NEWSROOM V1.0
Semantic Deduplication Engine: Multi-factor Entity & Media Hash Deduplication
"""
import re
from typing import List, Optional, Set, Tuple
from backend.app.database import get_db_connection, log_audit

def hamming_distance(hex1: str, hex2: str) -> int:
    """Compute Hamming distance between two hex hash strings."""
    if not hex1 or not hex2 or len(hex1) != len(hex2):
        return 999
    try:
        val1 = int(hex1, 16)
        val2 = int(hex2, 16)
        xor_val = val1 ^ val2
        return bin(xor_val).count("1")
    except Exception:
        return 999

def tokenize_title(title: str) -> Set[str]:
    """Tokenize and normalize Vietnamese title into meaningful content word set."""
    clean = re.sub(r"[^\w\s]", "", title.lower())
    words = set(clean.split())
    # Exclude common Vietnamese stopwords and filler words
    stopwords = {
        "và", "của", "tại", "ở", "với", "trong", "được", "cho", "là", "các", "những",
        "có", "không", "như", "đã", "sẽ", "đang", "ra", "vào", "lại", "thì", "mà",
        "bị", "khi", "từ", "lên", "về", "người", "qua", "sau", "trước", "nhau",
        "phải", "đến", "này", "đó", "vì", "do", "bởi", "nên", "nhiều", "ít", "rất", "quá",
        "cùng", "theo", "đây", "thế", "cả", "ai", "gì", "sao", "đâu", "đều", "mới", "vừa", "chỉ"
    }
    return words - stopwords

def compute_title_similarity(title1: str, title2: str) -> float:
    """Compute semantic containment & Jaccard similarity between two titles."""
    set1 = tokenize_title(title1)
    set2 = tokenize_title(title2)
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    jaccard = intersection / union if union > 0 else 0.0
    containment = intersection / min(len(set1), len(set2)) if min(len(set1), len(set2)) > 0 else 0.0
    # Combine Jaccard and containment score
    combined = max(jaccard, containment * 0.85)
    return round(combined, 3)

def check_duplicate_article(canonical_url: str, title: str, exclude_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if an incoming article is a duplicate of any scheduled, published post or active article.
    Checks:
    1. Exact canonical URL match in published/scheduled posts or articles.
    2. High title semantic similarity (>= 0.75) against already created posts or scheduled articles.
    (Note: Raw un-published or rejected articles do NOT block new article creation).
    """
    conn = get_db_connection()

    # 1. Exact canonical URL check against active posts
    query_exact = """
        SELECT p.id, a.title FROM posts p
        JOIN articles a ON p.article_id = a.id
        WHERE a.canonical_url = ? AND p.status NOT IN ('REJECTED', 'CANCELLED')
    """
    params_exact = [canonical_url]
    if exclude_id is not None:
        query_exact += " AND a.id != ?"
        params_exact.append(exclude_id)

    post_url_row = conn.execute(query_exact, params_exact).fetchone()
    if post_url_row:
        conn.close()
        return True, f"Bài viết này đã được tạo bài đăng #{post_url_row['id']}: '{post_url_row['title']}'"

    # 2. Check title similarity against active posts in the last 7 days
    query_active = """
        SELECT p.id, a.title FROM posts p
        JOIN articles a ON p.article_id = a.id
        WHERE p.status NOT IN ('REJECTED', 'CANCELLED') AND p.created_at >= datetime('now', '-7 days')
    """
    if exclude_id is not None:
        query_active += " AND a.id != ?"
        active_posts = conn.execute(query_active, (exclude_id,)).fetchall()
    else:
        active_posts = conn.execute(query_active).fetchall()

    for p in active_posts:
        orig = p["title"] or ""
        if orig:
            sim = compute_title_similarity(title, orig)
            if sim >= 0.75:
                conn.close()
                return True, f"Trùng nội dung (độ tương đồng {sim*100:.1f}%) với bài đăng #{p['id']}: '{orig}'"

    # 3. Check title similarity against articles already SCHEDULED or PUBLISHED
    scheduled_articles = conn.execute(
        "SELECT id, title FROM articles WHERE status IN ('SCHEDULED', 'PUBLISHED') AND collected_at >= datetime('now', '-7 days')"
    ).fetchall()

    for a in scheduled_articles:
        if exclude_id is not None and a["id"] == exclude_id:
            continue
        sim = compute_title_similarity(title, a["title"])
        if sim >= 0.75:
            conn.close()
            return True, f"Trùng nội dung (độ tương đồng {sim*100:.1f}%) với bài đã xếp lịch #{a['id']}: '{a['title']}'"

    conn.close()
    return False, None

def check_duplicate_media(sha256: str, phash: str) -> Tuple[bool, Optional[str]]:
    """
    Check if an incoming image has already been used or stored.
    Checks:
    1. Exact SHA-256 match.
    2. Perceptual Hash (dHash) with Hamming distance <= 5 (visual match).
    """
    conn = get_db_connection()

    # Exact SHA-256
    row = conn.execute("SELECT id, media_uuid FROM media WHERE sha256 = ?", (sha256,)).fetchone()
    if row:
        conn.close()
        return True, f"Trùng khớp SHA-256 với media #{row['id']} ({row['media_uuid']})"

    # Perceptual hash check
    if phash:
        rows = conn.execute("SELECT id, media_uuid, phash FROM media WHERE phash IS NOT NULL").fetchall()
        for r in rows:
            dist = hamming_distance(phash, r["phash"])
            if dist <= 5: # Near visual identical
                conn.close()
                return True, f"Trùng hình ảnh trực quan (Hamming dist={dist}) với media #{r['id']}"

    conn.close()
    return False, None
