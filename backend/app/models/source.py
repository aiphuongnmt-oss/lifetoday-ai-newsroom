"""
Source Registry Models & Schemas
"""
from pydantic import BaseModel
from typing import Optional

class SourceBase(BaseModel):
    id: str
    name: str
    url: str
    feed_url: Optional[str] = None
    country: str
    language: str
    default_category: str
    reliability_score: float = 0.8
    rate_limit_seconds: int = 60
    is_active: bool = True

class SourceCreate(SourceBase):
    pass

class SourceOut(SourceBase):
    last_checked_at: Optional[str] = None
    last_status: Optional[str] = "INITIAL"
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
