"""
LIFE TODAY — AI NEWSROOM V1.0
Single-Command Launcher
"""
import os
import sys
import threading
import time
import webbrowser
import uvicorn
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

PORT = int(os.getenv("PORT", "8000"))
IS_CLOUD = bool(os.getenv("SPACE_ID") or os.getenv("RENDER") or os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("CLOUD_DEPLOY"))

def open_browser():
    time.sleep(1.5)
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 65)
    print("   LIFE TODAY — AUTONOMOUS AI NEWSROOM V1.0")
    print("   Official Fanpage: https://www.facebook.com/lifetoday.vn")
    print("=" * 65)
    print(f"-> Starting Unified Dashboard at: http://0.0.0.0:{PORT}")
    print(f"-> Swagger API Docs available at: http://0.0.0.0:{PORT}/docs")
    print("-> Background Scheduler Daemon: ACTIVE")
    print("-> Press Ctrl+C to stop.")
    print("=" * 65)

    if not IS_CLOUD:
        threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=PORT, reload=False)
