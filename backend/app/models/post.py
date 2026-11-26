"""
Post Models & Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class PostBase(BaseModel):
    article_id: Optional[int] = None
    post_type: str = "ORIGINAL_PHOTO_POST"  # ORIGINAL_PHOTO_POST, TEXT_POST, LINK_POST
    category: str
    caption: str
    hashtags: Optional[str] = "#LifeToday"
    credit_source: Optional[str] = None
    operating_mode: str = "SHADOW_MODE"
    target_slot: Optional[str] = None
    scheduled_time: Optional[str] = None

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    credit_source: Optional[str] = None
    status: Optional[str] = None
    scheduled_time: Optional[str] = None
    target_slot: Optional[str] = None

class PostOut(PostBase):
    id: int
    post_uuid: str
    status: str
    published_time: Optional[str] = None
    fb_post_id: Optional[str] = None
    fb_permalink: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    media_items: Optional[List[dict]] = None

    class Config:
        from_attributes = True
