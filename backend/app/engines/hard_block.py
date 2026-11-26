"""
LIFE TODAY — AI NEWSROOM V1.0
Hard Block Engine: Zero-Tolerance Brand Safety & Pure Lifestyle Policy
Strictly excludes: Politics, Social issues, Crime, Accidents, Tragedies, Court disputes, Family hardships.
Only allows: Pure Entertainment, Fashion, Beauty, Travel, Cuisine, Culture & Arts.
"""
import re
from typing import Dict, List, Tuple
from backend.app.database import log_audit

HARD_BLOCK_RULES = {
    "POLITICS_AND_WAR": [
        r"\b(chính trị|bầu cử|quốc hội|chính phủ|thủ tướng|bộ trưởng|đại hội đảng|đảng cộng sản|nghị quyết|ủy ban|hội đồng nhân dân)\b",
        r"\b(chiến tranh|quân sự|vũ khí|tên lửa|chiến sự|nga-ukraine|israel|hamas|xung đột quân sự|chiến thắng 30/4)\b",
        r"\b(chủ quyền|biển đông|đường lưỡi bò|hoàng sa|trường sa|biên giới|ngoại giao)\b"
    ],
    "SOCIAL_AND_SENSITIVE_LIFE": [
        r"\b(thời sự|xã hội|dân sinh|đời sống khó khăn|cơ cực|túng thiếu|nghèo khổ|khốn đốn)\b",
        r"\b(tai nạn|va chạm|chìm tàu|rơi máy bay|cháy nổ|hỏa hoạn|sập cầu|sạt lở|lũ quét|đuối nước)\b",
        r"\b(tử vong|thiệt mạng|qua đời|chết|hôn mê|cấp cứu|nhập viện|bệnh nặng|ung thư|hiểm nghèo|thương tâm|tang lễ|đám tang|viếng|truy điệu|di nguyện)\b",
        r"\b(ly hôn|chia tay cay đắng|tranh chấp tài sản|kiện tụng|hầu tòa|tòa án|vụ kiện|phá sản|vỡ nợ|xiết nợ|phát mại)\b",
        r"\b(bắt cóc|ngược đãi|bạo hành|bạo lực gia đình|bạo lực|mẹ mìn|đánh đập|thương tích)\b"
    ],
    "CRIME_AND_LEGAL": [
        r"\b(tội phạm|hình sự|bắt tạm giam|tạm giam|khởi tố|điều tra|truy tố|tuyên án|tử hình|án mạng|giết người|sát hại|bị hại|ám sát)\b",
        r"\b(đi tù|ngồi tù|ở tù|chấp hành án|lãnh án|tuyên phạt|bắt giữ|vướng vòng lao lý|bị can|bị cáo|truy nã|tội ác)\b",
        r"\b(lừa đảo|tham nhũng|hối lộ|chiếm đoạt tài sản|rửa tiền|đường dây|triệt phá|buôn lậu)\b"
    ],
    "DRAMA_SCANDAL_EXPOSE": [
        r"\b(scandal|drama|bóc phốt|đấu tố|tin đồn|lộ clip|lộ ảnh nóng|ảnh riêng tư|lộ tin nhắn)\b",
        r"\b(ngoại tình|tiểu tam|trà xanh|đánh ghen|giật chồng|cướp người yêu|kẻ xấu đe dọa|đe dọa)\b",
        r"\b(fanwar|chửi bới|khẩu chiến|bạo lực mạng|body shaming|chê bai ngoại hình)\b"
    ],
    "SUBSTANCES_AND_GAMBLING": [
        r"\b(cờ bạc|cá độ|đánh bạc|game bài|tiền ảo đa cấp|bong88|bet88)\b",
        r"\b(ma túy|chất kích thích|cần sa|bóng cười|shisha|hút chích|nghiện ngập)\b"
    ],
    "OFFENSIVE_AND_MEDICAL": [
        r"\b(phản cảm|khiêu dâm|hở hang quá đà|lộ hàng|quấy rối|khỏa thân|phim 18\+|ảnh 18\+|nude|bán nude|cởi đồ|khoe da thịt|hở bạo)\b",
        r"\b(chữa ung thư|thuốc đông y gia truyền|tuyên bố y tế|thử thách nguy hiểm)\b"
    ]
}

def evaluate_hard_block(title: str, summary: str = "", content: str = "") -> Tuple[bool, str, str]:
    """
    Evaluate content against Life Today Hard Block Policy.
    Returns: (is_blocked: bool, block_reason: str, category: str)
    """
    full_text = f"{title} {summary} {content}".lower()

    for category, patterns in HARD_BLOCK_RULES.items():
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                matched_word = match.group(0)
                reason = f"Vi phạm chính sách an toàn [{category}]: phát hiện từ khóa cấm '{matched_word}'"
                log_audit("HARD_BLOCK_TRIGGERED", "HARD_BLOCK", f"Blocked: {reason} | Title: {title[:60]}")
                return True, reason, category

    if len(title.strip()) < 5:
        return True, "Tiêu đề quá ngắn hoặc không xác định được nội dung", "UNCLASSIFIED"

    return False, "", ""
