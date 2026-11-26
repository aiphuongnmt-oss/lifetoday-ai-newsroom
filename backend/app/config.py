"""
LIFE TODAY — AI NEWSROOM V1.0
Configuration Module
"""
import os
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, List

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "backend" / "data"
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "lifetoday.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# System Metadata
APP_NAME = "LIFE TODAY — AI NEWSROOM"
APP_VERSION = "1.0.0"
FACEBOOK_PAGE_URL = "https://www.facebook.com/lifetoday.vn"
TIMEZONE = "Asia/Ho_Chi_Minh"

# Standard Content Mix Ratios (7-day / 30-day tracking targets)
DEFAULT_CONTENT_MIX: Dict[str, float] = {
    "Showbiz": 0.20,
    "Phim ảnh": 0.15,
    "Âm nhạc": 0.10,
    "Thời trang và làm đẹp": 0.20,
    "Du lịch": 0.20,
    "Ẩm thực": 0.05,
    "Văn hóa và nghệ thuật": 0.05,
    "Trending": 0.05,
}

# Standard Publishing Slots (Daily, Asia/Ho_Chi_Minh)
DEFAULT_PUBLISH_SLOTS: List[str] = [
    "07:30",
    "10:00",
    "12:00",
    "15:00",
    "18:00",
    "20:30"
]

# Standard Daily Hunting Cycles
DEFAULT_HUNT_CYCLES: List[str] = [
    "06:30",
    "11:00",
    "17:00"
]

MAX_POSTS_PER_DAY = 6

# Operating Modes
OPERATING_MODES = ["MANUAL", "SEMI_AUTO", "FULL_AUTO", "SHADOW_MODE"]
DEFAULT_OPERATING_MODE = "SHADOW_MODE"

# Meta Graph API Default Version
META_GRAPH_API_VERSION = "v21.0"
META_GRAPH_API_BASE = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"

# Environment Variables
def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)
