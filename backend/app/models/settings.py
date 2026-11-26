"""
Settings Models & Schemas
"""
from pydantic import BaseModel
from typing import Dict, Optional

class SystemSettingsUpdate(BaseModel):
    operating_mode: Optional[str] = None
    emergency_stop: Optional[bool] = None
    content_mix: Optional[Dict[str, float]] = None
    meta_page_id: Optional[str] = None
    meta_page_access_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_host: Optional[str] = None
    ollama_model: Optional[str] = None

class SystemStatusOut(BaseModel):
    app_name: str
    version: str
    operating_mode: str
    emergency_stop: bool
    content_mix: Dict[str, float]
    articles_count: int
    pending_posts_count: int
    scheduled_posts_count: int
    published_posts_count: int
    meta_connected: bool
    meta_page_id: Optional[str]
