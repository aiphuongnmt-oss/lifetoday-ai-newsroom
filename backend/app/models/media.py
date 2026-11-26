"""
Media Models & Schemas
"""
from pydantic import BaseModel
from typing import Optional

class MediaBase(BaseModel):
    article_id: Optional[int] = None
    post_id: Optional[int] = None
    original_url: str
    local_path: Optional[str] = None
    file_format: Optional[str] = None
    width: int = 0
    height: int = 0
    aspect_ratio: float = 0.0
    file_size_bytes: int = 0
    sharpness_score: float = 0.0
    sha256: Optional[str] = None
    phash: Optional[str] = None
    quality_status: str = "UNVERIFIED" # QUALIFIED, LOW_RES, BLURRY, CORRUPTED, UNVERIFIED
    rights_status: str = "WAITING_FOR_RIGHTS" # VERIFIED_FREE, PRESS_KIT, LICENSED, WAITING_FOR_RIGHTS, REJECTED
    rights_source: Optional[str] = None
    author_owner: Optional[str] = None
    license_type: Optional[str] = None
    credit_required: Optional[str] = None

class MediaCreate(MediaBase):
    pass

class MediaOut(MediaBase):
    id: int
    media_uuid: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class MediaRightsUpdate(BaseModel):
    rights_status: str
    rights_source: Optional[str] = None
    author_owner: Optional[str] = None
    license_type: Optional[str] = None
    credit_required: Optional[str] = None
