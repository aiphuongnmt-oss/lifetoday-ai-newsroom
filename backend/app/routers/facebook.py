"""
Router: Facebook Connection & Feed
"""
from fastapi import APIRouter
from backend.app.engines.facebook_publisher import FacebookPublisher

router = APIRouter(prefix="/api/facebook", tags=["Facebook"])

@router.get("/status")
async def get_facebook_status():
    """Test Facebook Graph API connection with configured credentials."""
    pub = FacebookPublisher()
    return await pub.test_connection()
