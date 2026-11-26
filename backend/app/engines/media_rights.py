"""
LIFE TODAY — AI NEWSROOM V1.0
Media Rights Engine: Strict Intellectual Property & Personal Image Rights Verification
"""
from typing import Dict, List, Optional, Tuple
from backend.app.database import get_db_connection, log_audit

VALID_RIGHTS_STATUSES = [
    "VERIFIED_FREE",      # Explicitly free for editorial use / public PR kit
    "PRESS_KIT",          # Official press kit from agency / brand / studio
    "LICENSED",           # Direct license agreement / contract
    "WAITING_FOR_RIGHTS", # Default state: hold until verified
    "REJECTED"            # Unusable / copyrighted without permission
]

def check_media_publishable(media_item: dict) -> Tuple[bool, str]:
    """
    Check if a media item is legally cleared for publication.
    Under Life Today policy, WAITING_FOR_RIGHTS or REJECTED cannot be published.
    """
    rights_status = media_item.get("rights_status", "WAITING_FOR_RIGHTS")
    quality_status = media_item.get("quality_status", "UNVERIFIED")

    if quality_status != "QUALIFIED":
        return False, f"Ảnh chưa đạt chuẩn chất lượng kỹ thuật ({quality_status})"

    if rights_status not in ("VERIFIED_FREE", "PRESS_KIT", "LICENSED"):
        return False, f"Ảnh chưa được xác thực quyền sử dụng ({rights_status}). Đang ở chế độ WAITING_FOR_RIGHTS."

    return True, "Đủ điều kiện xuất bản"

def update_media_rights(
    media_uuid: str,
    rights_status: str,
    rights_source: Optional[str] = None,
    author_owner: Optional[str] = None,
    license_type: Optional[str] = None,
    credit_required: Optional[str] = None
) -> Dict:
    """Update media rights metadata in SQLite."""
    if rights_status not in VALID_RIGHTS_STATUSES:
        raise ValueError(f"Invalid rights status: {rights_status}")

    conn = get_db_connection()
    conn.execute("""
        UPDATE media SET
            rights_status = ?,
            rights_source = COALESCE(?, rights_source),
            author_owner = COALESCE(?, author_owner),
            license_type = COALESCE(?, license_type),
            credit_required = COALESCE(?, credit_required)
        WHERE media_uuid = ?
    """, (rights_status, rights_source, author_owner, license_type, credit_required, media_uuid))
    conn.commit()
    conn.close()

    log_audit("MEDIA_RIGHTS_UPDATED", "MEDIA_RIGHTS", f"Updated {media_uuid} to {rights_status}")
    return {"media_uuid": media_uuid, "rights_status": rights_status}
