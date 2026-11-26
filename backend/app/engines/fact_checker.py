"""
LIFE TODAY — AI NEWSROOM V1.0
Fact Checking & Legal Compliance Engine
"""
import re
from typing import Dict, List, Optional, Tuple
from backend.app.database import log_audit

# Ambassadorship Title Strict Hierarchy
AMBASSADOR_TIERS = {
    "GLOBAL_AMBASSADOR": {
        "vi": "Đại sứ toàn cầu",
        "keywords": ["global ambassador", "global brand ambassador", "đại sứ toàn cầu"]
    },
    "BRAND_AMBASSADOR": {
        "vi": "Đại sứ thương hiệu",
        "keywords": ["brand ambassador", "đại sứ thương hiệu", "đại sứ"]
    },
    "HOUSE_AMBASSADOR": {
        "vi": "Đại sứ nhà mốt",
        "keywords": ["house ambassador", "đại sứ nhà mốt", "đại sứ dòng"]
    },
    "FRIEND_OF_HOUSE": {
        "vi": "Bạn thân thương hiệu",
        "keywords": ["friend of the house", "bạn thân nhà mốt", "bạn thân thương hiệu"]
    },
    "CAMPAIGN_FACE": {
        "vi": "Gương mặt chiến dịch",
        "keywords": ["campaign face", "face of the campaign", "gương mặt quảng bá", "gương mặt chiến dịch"]
    },
    "GUEST": {
        "vi": "Khách mời",
        "keywords": ["guest", "attendee", "khách mời", "tham dự với tư cách khách mời"]
    }
}

KNOWN_FASHION_HOUSES = [
    "Chanel", "Dior", "Gucci", "Louis Vuitton", "Saint Laurent", "YSL", "Prada",
    "Celine", "Bottega Veneta", "Versace", "Balenciaga", "Fendi", "Valentino",
    "Givenchy", "Burberry", "Loewe", "Miu Miu", "Hermès", "Cartier", "Bvlgari",
    "Tiffany & Co.", "Van Cleef & Arpels", "Chopard", "Armani"
]

def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract key named entities from news text."""
    entities = {
        "brands": [],
        "ambassador_titles": [],
        "events": [],
        "dates_or_locations": []
    }

    # Brand recognition
    for brand in KNOWN_FASHION_HOUSES:
        if re.search(rf"\b{re.escape(brand)}\b", text, re.IGNORECASE):
            entities["brands"].append(brand)

    # Ambassador hierarchy check
    lower_text = text.lower()
    for tier_code, tier_info in AMBASSADOR_TIERS.items():
        for kw in tier_info["keywords"]:
            if kw in lower_text:
                entities["ambassador_titles"].append(f"{tier_info['vi']} ({tier_code})")
                break

    # Major events
    events = ["Fashion Week", "Met Gala", "Cannes", "Oscar", "Grammy", "Billboard", "Coachella", "Concert", "Fan Meeting"]
    for ev in events:
        if re.search(rf"\b{re.escape(ev)}\b", text, re.IGNORECASE):
            entities["events"].append(ev)

    return entities

def verify_facts_and_compliance(
    title: str,
    summary: str,
    source_reliability: float
) -> Tuple[str, Dict]:
    """
    Verify facts, ambassador distinctions, and legal compliance.
    Returns status: 'VERIFIED', 'HOLD_NEEDS_REVIEW', or 'REJECTED'
    along with fact metadata.
    """
    full_text = f"{title} {summary}"
    entities = extract_entities(full_text)

    # Ambiguity check for ambassadorship
    # If title claims Global Ambassador but text says Friend of House -> mismatch
    claimed_global = any("GLOBAL_AMBASSADOR" in t for t in entities["ambassador_titles"])
    claimed_friend = any("FRIEND_OF_HOUSE" in t for t in entities["ambassador_titles"])

    verification_status = "VERIFIED"
    notes = []

    if claimed_global and claimed_friend:
        verification_status = "HOLD_NEEDS_REVIEW"
        notes.append("Cần xác minh danh xưng: Phát hiện mâu thuẫn giữa Đại sứ toàn cầu và Bạn thân thương hiệu")

    # If source reliability is low (< 0.8) and it's an unconfirmed major claim
    if source_reliability < 0.8:
        verification_status = "HOLD_NEEDS_REVIEW"
        notes.append("Nguồn có độ tin cậy trung bình, cần kiểm chứng chéo trước khi xuất bản")

    # Vietnamese Press Law compliance: Ensure we are presenting curatorial/social facts, not claiming exclusive journalistic credentials
    press_indicators = ["phóng viên chúng tôi", "báo chúng tôi độc quyền", "theo điều tra riêng"]
    for pi in press_indicators:
        if pi in full_text.lower():
            verification_status = "HOLD_NEEDS_REVIEW"
            notes.append(f"Cảnh báo tuân thủ Luật Báo chí: Chứa tuyên bố tác nghiệp báo chí '{pi}'")

    audit_msg = f"Fact Check: {verification_status} | Brands: {entities['brands']} | Notes: {notes}"
    log_audit("FACT_CHECK_EVALUATION", "FACT_CHECKER", audit_msg)

    return verification_status, {
        "entities": entities,
        "notes": notes,
        "source_reliability": source_reliability
    }
