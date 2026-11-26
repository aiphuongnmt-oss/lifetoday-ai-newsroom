"""
Router: Source Registry
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel

from backend.app.database import get_db_connection, log_audit
from backend.app.engines.source_registry import get_all_sources, check_source_health

router = APIRouter(prefix="/api/sources", tags=["Sources"])

class SourceUpdate(BaseModel):
    is_active: Optional[bool] = None
    default_category: Optional[str] = None
    rate_limit_seconds: Optional[int] = None
    reliability_score: Optional[float] = None

@router.get("")
def list_sources(active_only: bool = False):
    """List registered sources."""
    return get_all_sources(active_only=active_only)

@router.post("/{source_id}/check")
async def check_source(source_id: str):
    """Trigger health check on a source feed."""
    return await check_source_health(source_id)

@router.put("/{source_id}")
def update_source(source_id: str, payload: SourceUpdate):
    """Update source parameters."""
    conn = get_db_connection()
    updates = []
    params = []

    if payload.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if payload.is_active else 0)
    if payload.default_category is not None:
        updates.append("default_category = ?")
        params.append(payload.default_category)
    if payload.rate_limit_seconds is not None:
        updates.append("rate_limit_seconds = ?")
        params.append(payload.rate_limit_seconds)
    if payload.reliability_score is not None:
        updates.append("reliability_score = ?")
        params.append(payload.reliability_score)

    if updates:
        params.append(source_id)
        conn.execute(f"UPDATE sources SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    conn.close()
    log_audit("SOURCE_UPDATED", "SOURCE_ROUTER", f"Source {source_id} updated")
    return {"success": True, "source_id": source_id}
