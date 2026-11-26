"""
Router: Media Storage & Rights Verification
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional

from backend.app.database import get_db_connection
from backend.app.models.media import MediaRightsUpdate
from backend.app.engines.media_rights import update_media_rights

router = APIRouter(prefix="/api/media", tags=["Media"])

@router.get("")
def list_media(
    quality_status: Optional[str] = None,
    rights_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List media assets with quality and rights filters."""
    conn = get_db_connection()
    query = "SELECT * FROM media WHERE 1=1"
    params = []

    if quality_status:
        query += " AND quality_status = ?"
        params.append(quality_status)
    if rights_status:
        query += " AND rights_status = ?"
        params.append(rights_status)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.put("/{media_uuid}/rights")
def set_media_rights(media_uuid: str, payload: MediaRightsUpdate):
    """Update usage rights clearance for an image."""
    try:
        res = update_media_rights(
            media_uuid=media_uuid,
            rights_status=payload.rights_status,
            rights_source=payload.rights_source,
            author_owner=payload.author_owner,
            license_type=payload.license_type,
            credit_required=payload.credit_required
        )
        return {"success": True, **res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
