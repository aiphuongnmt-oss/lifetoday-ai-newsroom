"""
LIFE TODAY — AI NEWSROOM V1.0
Automatic Multilingual Translation & Localization Engine (English/Korean/Chinese -> Vietnamese)
"""
import re
from typing import Dict, Optional
import httpx
from backend.app.database import get_setting

# Common entertainment & lifestyle dictionary for instant offline translation
HEADLINE_TRANSLATIONS = {
    # Red carpet & fashion
    r"breakout red carpet stars": "những ngôi sao thảm đỏ đột phá",
    r"red carpet": "thảm đỏ",
    r"best dressed": "mặc đẹp nhất",
    r"fashion week": "tuần lễ thời trang",
    r"runway": "sàn diễn thời trang",
    r"veil alternatives for the bride": "gợi ý khăn voan độc đáo cho cô dâu",
    r"steals the spotlight": "chiếm trọn tâm điểm",
    r"stunning in": "lộng lẫy trong trang phục",
    r"haute couture": "thời trang cao cấp Haute Couture",
    r"brand ambassador": "đại sứ thương hiệu",
    r"global ambassador": "đại sứ toàn cầu",

    # Entertainment & Film
    r"box office": "phòng vé",
    r"breaks record": "phá kỷ lục",
    r"trailer released": "tung trailer chính thức",
    r"teaser released": "hé lộ teaser mới",
    r"confirms release date": "chốt ngày khởi chiếu",
    r"steps down from": "rút khỏi dự án",
    r"announces marriage": "thông báo kết hôn",
    r"goes undercover": "hóa thân mật vụ",
    r"in new film": "trong phim điện ảnh mới",
    r"new comedy film": "phim hài mới",
    r"teases journey": "hé lộ hành trình",
    r"sustains injury": "gặp chấn thương",
    r"shares thoughts on": "chia sẻ về",
    r"talks about": "lên tiếng về",
    r"watch:": "xem ngay:",

    # Travel & Lifestyle
    r"best airbnbs in": "những homestay/Airbnb đẹp nhất tại",
    r"embrace hygge": "mang phong cách sống ấm cúng",
    r"best restaurants in": "những nhà hàng ngon nhất tại",
    r"luckiest zodiac signs": "những chòm sao may mắn nhất",
    r"sagittarius season": "mùa Nhân Mã",
    r"how women weavers are preserving": "cách những người phụ nữ gìn giữ nghề dệt",
    r"indigenous amazigh culture in morocco": "văn hóa bản địa Amazigh tại Morocco",
    r"the 38 best london restaurants": "38 nhà hàng xuất sắc nhất tại London",
    r"the best holiday gifts": "gợi ý quà tặng mùa lễ hội ý nghĩa nhất",
    r"celebrating the eater awards": "vinh danh giải thưởng ẩm thực Eater Awards"
}

def translate_headline_rule_based(text: str) -> str:
    """Translate common entertainment headlines using rule-based dictionary."""
    clean = text.strip()
    result = clean

    # Check for direct mapping phrases
    for en_pat, vi_rep in HEADLINE_TRANSLATIONS.items():
        result = re.sub(en_pat, vi_rep, result, flags=re.IGNORECASE)

    # Clean up patterns like "Watch: "
    result = re.sub(r"^Watch:\s*", "", result, flags=re.IGNORECASE)

    return result

async def translate_to_vietnamese(text: str, context: str = "Tiêu đề tin tức giải trí") -> str:
    """
    Translate English text to natural Vietnamese using:
    1. Gemini API (if key available)
    2. Rule-based dictionary + linguistic structure (offline fallback)
    """
    if not text or not text.strip():
        return ""

    # Check if text is already mostly Vietnamese
    vietnamese_chars = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
    if any(c in vietnamese_chars for c in text.lower()):
        return text

    gemini_key = get_setting("gemini_api_key")
    if gemini_key:
        try:
            prompt = f"Dịch tiêu đề sau từ tiếng Anh sang tiếng Việt tự nhiên, tinh tế, chuẩn xác cho cộng đồng giải trí Life Today. Chỉ trả về một câu tiếng Việt duy nhất:\n\n{text}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                resp = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
                if resp.status_code == 200:
                    data = resp.json()
                    translated = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if translated:
                        return translated
        except Exception:
            pass

    # High quality rule-based fallback
    return translate_headline_rule_based(text)
