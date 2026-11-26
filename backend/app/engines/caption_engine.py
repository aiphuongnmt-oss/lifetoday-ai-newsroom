"""
LIFE TODAY — AI NEWSROOM V1.0
AI Caption Engine: Aesthetic, Concise Vietnamese Social Editorial Generator
"""
import re
import httpx
from typing import Dict, List, Optional
from backend.app.database import get_setting, log_audit

WORD_COUNT_LIMITS = {
    "Bộ ảnh nghệ sĩ": (15, 40),
    "Showbiz": (20, 60),
    "Thời trang và làm đẹp": (20, 60),
    "Phim ảnh": (30, 80),
    "Âm nhạc": (30, 80),
    "Du lịch": (40, 100),
    "Trending": (15, 50),
    "Ẩm thực": (25, 70),
    "Văn hóa và nghệ thuật": (25, 70)
}

# Cliché phrases that are strictly filtered out
FORBIDDEN_CLICHES = [
    r"hãy cùng life today khám phá",
    r"bạn nghĩ sao về",
    r"không thể phủ nhận rằng",
    r"hãy để lại bình luận",
    r"chắc hẳn bạn đã biết",
    r"cùng đón chờ nhé",
    r"cực hot",
    r"gây bão mạng xã hội",
    r"chao đảo cộng đồng mạng"
]

def clean_cliches(text: str) -> str:
    """Strip out robotic or sensational AI clichés."""
    result = text
    for cliché in FORBIDDEN_CLICHES:
        result = re.sub(cliché, "", result, flags=re.IGNORECASE)
    # Clean double spaces or leading/trailing punctuation issues
    result = re.sub(r"\s+", " ", result).strip()
    result = re.sub(r"^[,\.\?!:\s]+", "", result)
    return result

def generate_hashtags(category: str, entities: Optional[Dict] = None) -> str:
    """Generate 3-5 curated, relevant hashtags including #LifeToday."""
    tags = ["#LifeToday"]

    category_tag_map = {
        "Showbiz": ["#Showbiz", "#SaoViet", "#Celeb"],
        "Thời trang và làm đẹp": ["#Fashion", "#ThoiTrang", "#Style"],
        "Phim ảnh": ["#Movie", "#PhimHay", "#Cinema"],
        "Âm nhạc": ["#Music", "#AmNhac", "#Vpop"],
        "Du lịch": ["#Travel", "#DuLich", "#Checkin"],
        "Ẩm thực": ["#Foodie", "#AmThuc", "#Delicious"],
        "Văn hóa và nghệ thuật": ["#Art", "#VanHoa", "#LifeStyle"],
        "Trending": ["#Trending", "#XuHuong", "#Viral"]
    }

    base_tags = category_tag_map.get(category, ["#Trending", "#Lifestyle"])
    for t in base_tags:
        if len(tags) < 4:
            tags.append(t)

    # Add brand or event tag if detected
    if entities:
        for b in entities.get("brands", [])[:1]:
            tags.append(f"#{re.sub(r'[^a-zA-Z0-9]', '', b)}")

    return " ".join(tags[:5])

def clean_press_prefixes(text: str) -> str:
    """Strip out journalistic wire prefixes like 'THỤY SĨ –', '(Dân trí) -', 'HÀ NỘI -'."""
    if not text:
        return ""
    # Strip (Dân trí) -, (VnExpress) -, [VietnamNet] -, etc.
    cleaned = re.sub(r"^[\(\[\{][^\)\]\}]+[\)\]\}]\s*[-–—:]\s*", "", text).strip()
    # Strip location prefixes: THỤY SĨ –, HÀ NỘI –, TP.HCM –, v.v.
    cleaned = re.sub(r"^[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ\s\./]{2,20}\s*[-–—:]\s*", "", cleaned).strip()
    # Strip common leading words
    cleaned = re.sub(r"^(Ảnh|Video|Nóng|Mới|Tin tức|Hé lộ|Bật mí):\s*", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned

def synthesize_rule_based_caption(
    title: str,
    summary: str,
    category: str,
    entities: Optional[Dict] = None,
    credit_source: str = ""
) -> str:
    """
    Expert Vietnamese linguistic synthesis engine.
    Ensures natural, engaging social media style even when running offline without Gemini API Key.
    """
    clean_t = clean_press_prefixes(title)
    clean_s = clean_cliches(clean_press_prefixes(summary or ""))

    # Select the most informative, fluent sentence from summary
    body_sentence = ""
    if clean_s:
        sentences = re.split(r"(?<=[.!?])\s+", clean_s)
        for s in sentences:
            s_clean = s.strip()
            # Pick a rich descriptive sentence that is not a promotional call to action
            if len(s_clean) > 25 and not any(k in s_clean.lower() for k in ["bấm vào", "xem thêm", "nguồn", "theo dõi", "liên hệ"]):
                body_sentence = s_clean
                if not body_sentence.endswith((".", "!", "?")):
                    body_sentence += "."
                break

    # Natural social editorial synthesis based on category
    if category == "Du lịch":
        if body_sentence and clean_t.lower() not in body_sentence.lower():
            caption_body = f"{clean_t}. {body_sentence}"
        elif body_sentence:
            caption_body = body_sentence
        else:
            caption_body = f"Khám phá điểm đến tuyệt đẹp: {clean_t}."
    elif category == "Showbiz":
        if body_sentence and clean_t.lower() not in body_sentence.lower():
            caption_body = f"{clean_t}. {body_sentence}"
        elif body_sentence:
            caption_body = body_sentence
        else:
            caption_body = f"Cập nhật mới nhất: {clean_t}."
    elif category == "Ẩm thực":
        if body_sentence and clean_t.lower() not in body_sentence.lower():
            caption_body = f"Gợi ý hấp dẫn dành cho các tín đồ ẩm thực: {clean_t}. {body_sentence}"
        else:
            caption_body = f"Gợi ý ẩm thực đặc sắc: {clean_t}."
    elif category == "Thời trang và làm đẹp":
        if body_sentence and clean_t.lower() not in body_sentence.lower():
            caption_body = f"Nổi bật trong phong cách: {clean_t}. {body_sentence}"
        else:
            caption_body = f"Phong cách và xu hướng: {clean_t}."
    else:
        if body_sentence and clean_t.lower() not in body_sentence.lower():
            caption_body = f"{clean_t}. {body_sentence}"
        else:
            caption_body = f"{clean_t}."

    caption_body = clean_cliches(caption_body)

    # Check word count limits
    words = caption_body.split()
    min_w, max_w = WORD_COUNT_LIMITS.get(category, (20, 60))
    if len(words) > max_w:
        caption_body = " ".join(words[:max_w]).rstrip(",;:-") + "..."

    return caption_body

async def generate_caption_ai(
    title: str,
    summary: str,
    category: str,
    entities: Optional[Dict] = None,
    credit_source: str = ""
) -> Dict[str, str]:
    """
    Generate final aesthetic Vietnamese caption with priority:
    1. Gemini Free Tier (if configured)
    2. Ollama Local (if running)
    3. Built-in Editorial Synthesis Engine (guaranteed fallback)
    """
    gemini_key = get_setting("gemini_api_key")
    ollama_host = get_setting("ollama_host", "http://localhost:11434")

    hashtags = generate_hashtags(category, entities)
    caption_text = ""
    engine_used = "BUILTIN_SYNTHESIS"

    # Attempt Gemini API Free Tier if key is provided
    if gemini_key:
        try:
            prompt = f"""Bạn là biên tập viên xuất sắc của fanpage LIFE TODAY (chuyên trang giải trí, phong cách sống, du lịch và thời trang).
Hãy đọc kỹ thông tin bài báo dưới đây và VIẾT LẠI thành 1 bài đăng Facebook (caption) tự nhiên, cuốn hút, hấp dẫn:

Chuyên mục: {category}
Tiêu đề: {title}
Nội dung/Tóm tắt: {summary}

Quy chuẩn viết bài:
- Viết lại bằng giọng văn của một admin page sành điệu, trẻ trung, tinh tế, giới thiệu thông tin thú vị tới bạn đọc.
- BÀI ĐĂNG PHẢI CUNG CẤP THÔNG TIN TRỌN VẸN: Nêu rõ sự kiện chính (nói rõ sự việc, nhân vật, bối cảnh), KHÔNG viết lấp lửng hay úp mở nửa vời khiến người đọc phải tìm link đọc tiếp. Độc giả lướt Facebook chỉ cần đọc caption và xem ảnh là nắm trọn vẹn câu chuyện.
- TUYỆT ĐỐI KHÔNG chép lại nguyên văn tiêu đề báo chí khô khan. Hãy dùng từ ngữ mượt mà, gợi mở hình ảnh và cảm xúc.
- Độ dài: 2 đến 4 câu ngắn gọn, súc tích (khoảng {WORD_COUNT_LIMITS.get(category, (20, 60))[0]}-{WORD_COUNT_LIMITS.get(category, (20, 60))[1]} từ).
- Không dùng từ ngữ sáo rỗng (như 'Hãy cùng...', 'Bạn nghĩ sao', 'Cực hot', 'Gây bão').
- Trả về DUY NHẤT nội dung caption, không kèm tiêu đề, không giải thích."""

            async with httpx.AsyncClient(timeout=25.0) as client:
                models_to_try = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]
                for model_name in models_to_try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
                    resp = await client.post(url, json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 2500,
                            "thinkingConfig": {
                                "thinkingBudget": 256
                            }
                        }
                    })
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            cand = candidates[0]
                            raw_text = cand.get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                            # Ensure caption is a complete, un-truncated sentence ending with proper punctuation
                            if raw_text and len(raw_text.split()) >= 15 and raw_text.rstrip().endswith((".", "!", "?", '"', '”')):
                                caption_text = clean_cliches(raw_text)
                                engine_used = f"GEMINI_AI ({model_name})"
                                break
        except Exception as e:
            print(f"Gemini API call failed, falling back: {e}")

    # Fallback to Built-in Synthesis if still empty
    if not caption_text:
        caption_text = synthesize_rule_based_caption(
            title=title,
            summary=summary,
            category=category,
            entities=entities,
            credit_source=credit_source
        )
        engine_used = "BUILTIN_EDITORIAL_ENGINE"

    # Format final caption with credit and hashtags
    credit_line = f"Ảnh / Nguồn: {credit_source}" if credit_source else ""
    final_output = f"{caption_text}\n\n{hashtags}"
    if credit_line:
        final_output += f"\n{credit_line}"

    log_audit("CAPTION_GENERATED", "CAPTION_ENGINE", f"Engine: {engine_used} | Category: {category} | Words: {len(caption_text.split())}")

    return {
        "caption": caption_text,
        "hashtags": hashtags,
        "credit_line": credit_line,
        "full_post_text": final_output,
        "word_count": len(caption_text.split()),
        "engine_used": engine_used
    }
