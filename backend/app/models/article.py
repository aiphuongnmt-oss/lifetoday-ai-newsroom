"""
Article Models & Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ArticleBase(BaseModel):
    guid: str
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None
    url: str
    canonical_url: Optional[str] = None
    source_id: Optional[str] = None
    source_name: Optional[str] = None
    country: Optional[str] = "VN"
    language: Optional[str] = "vi"
    category: Optional[str] = "Showbiz"
    published_at: Optional[str] = None

class ArticleCreate(ArticleBase):
    raw_data: Optional[Dict[str, Any]] = None

class ArticleOut(ArticleBase):
    id: int
    collected_at: Optional[str] = None
    verified_at: Optional[str] = None
    trend_score: float = 0.0
    trend_breakdown: Optional[str] = None
    status: str = "NEW"
    hard_block_reason: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class ArticleFilter(BaseModel):
    category: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None
    time_range: Optional[str] = None # 30m, 1h, 3h, 6h, today, 24h
    keyword: Optional[str] = None
