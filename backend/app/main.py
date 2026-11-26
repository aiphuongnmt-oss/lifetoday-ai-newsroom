"""
LIFE TODAY — AI NEWSROOM V1.0
FastAPI Application Entrypoint
"""
import os
import hmac
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.config import APP_NAME, APP_VERSION, MEDIA_DIR, BASE_DIR
from backend.app.database import init_db, log_audit
from backend.app.engines.source_registry import seed_source_registry
from backend.app.engines.scheduler_worker import start_autonomous_daemon
import asyncio

from backend.app.routers.news import router as news_router
from backend.app.routers.posts import router as posts_router
from backend.app.routers.media import router as media_router
from backend.app.routers.sources import router as sources_router
from backend.app.routers.settings import router as settings_router
from backend.app.routers.facebook import router as facebook_router
from backend.app.routers.analytics import router as analytics_router

FRONTEND_DIR = BASE_DIR / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database & Seed Source Registry
    init_db()
    seed_source_registry()
    log_audit("SYSTEM_STARTUP", "LIFECYCLE", f"{APP_NAME} v{APP_VERSION} initialized")

    # Start autonomous background scheduler daemon
    daemon_task = asyncio.create_task(start_autonomous_daemon())
    yield
    # Shutdown
    daemon_task.cancel()
    try:
        await daemon_task
    except asyncio.CancelledError:
        pass
    log_audit("SYSTEM_SHUTDOWN", "LIFECYCLE", f"{APP_NAME} shut down")

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Autonomous AI Newsroom for Life Today (https://www.facebook.com/lifetoday.vn)",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional PIN Protection Middleware (active when ACCESS_PIN env var is set on Cloud)
@app.middleware("http")
async def pin_auth_middleware(request: Request, call_next):
    required_pin = os.getenv("ACCESS_PIN", "").strip()
    path = request.url.path
    if required_pin and path.startswith("/api/") and path not in ("/api/health", "/api/auth/status", "/api/auth/verify"):
        provided_pin = request.headers.get("X-Newsroom-Pin", "").strip()
        if not provided_pin or not hmac.compare_digest(provided_pin, required_pin):
            return JSONResponse(status_code=401, content={"detail": "Vui lòng nhập mã PIN truy cập phòng tin."})
    return await call_next(request)

@app.get("/api/auth/status")
def auth_status():
    return {"pin_required": bool(os.getenv("ACCESS_PIN", "").strip())}

@app.post("/api/auth/verify")
async def auth_verify(request: Request):
    required_pin = os.getenv("ACCESS_PIN", "").strip()
    if not required_pin:
        return {"valid": True}
    body = await request.json()
    provided_pin = str(body.get("pin", "")).strip()
    if hmac.compare_digest(provided_pin, required_pin):
        return {"valid": True}
    return JSONResponse(status_code=401, content={"valid": False, "detail": "Mã PIN không đúng, vui lòng thử lại."})

# Include API Routers
app.include_router(news_router)
app.include_router(posts_router)
app.include_router(media_router)
app.include_router(sources_router)
app.include_router(settings_router)
app.include_router(facebook_router)
app.include_router(analytics_router)

# Mount Static Media Directory
if MEDIA_DIR.exists():
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Mount Frontend static files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/api/health")
def health_check():
    return {"status": "ONLINE", "app": APP_NAME, "version": APP_VERSION}

@app.get("/")
def serve_frontend_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": f"Welcome to {APP_NAME} API. Visit /docs for Swagger UI."}
