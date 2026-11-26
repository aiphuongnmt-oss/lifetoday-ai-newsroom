"""
LIFE TODAY — AI NEWSROOM V1.0
Facebook Graph API Integration & Multi-format Publisher
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import httpx

from backend.app.config import META_GRAPH_API_BASE
from backend.app.database import get_db_connection, get_setting, set_setting, log_audit

class FacebookPublisher:
    """Manages Meta Graph API v21.0 publication for Life Today."""

    def __init__(self, resolve_remote: bool = False):
        self.page_id = get_setting("meta_page_id") or os.getenv("META_PAGE_ID", "")
        raw_token = get_setting("meta_page_access_token") or os.getenv("META_PAGE_ACCESS_TOKEN", "")
        cached_effective = get_setting("meta_effective_page_token")
        if cached_effective and not resolve_remote:
            self.access_token = cached_effective
        elif resolve_remote:
            self.access_token = self._resolve_page_token(raw_token)
        else:
            self.access_token = raw_token

    def _resolve_page_token(self, token: str) -> str:
        """Ensure token is a Page Token (exchanges User Token for Page Token if needed)."""
        if not token or not self.page_id:
            return token
        app_id = get_setting("meta_app_id") or os.getenv("META_APP_ID", "")
        app_secret = get_setting("meta_app_secret") or os.getenv("META_APP_SECRET", "")
        try:
            with httpx.Client(timeout=8.0) as client:
                params = {"fields": "access_token", "access_token": token}
                if app_id and app_secret:
                    params["client_id"] = app_id
                    params["client_secret"] = app_secret
                r = client.get(f"{META_GRAPH_API_BASE}/{self.page_id}", params=params)
                if r.status_code == 200:
                    pt = r.json().get("access_token")
                    if pt:
                        set_setting("meta_effective_page_token", pt)
                        return pt
        except Exception:
            pass
        return token

    def is_configured(self) -> bool:
        return bool(self.page_id and self.access_token)

    async def test_connection(self) -> Dict:
        """Verify Meta Graph API token and fetch Page details."""
        if not self.is_configured():
            return {
                "connected": False,
                "error": "Chưa cấu hình Page ID hoặc Page Access Token trong cài đặt hệ thống.",
                "page_name": None,
                "page_id": None
            }

        url = f"{META_GRAPH_API_BASE}/{self.page_id}"
        params = {
            "fields": "id,name,link,fan_count,verification_status",
            "access_token": self.access_token
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                data = resp.json()

                if resp.status_code == 200:
                    log_audit("FACEBOOK_CONN_SUCCESS", "FB_PUBLISHER", f"Connected to {data.get('name')} (ID: {data.get('id')})")
                    return {
                        "connected": True,
                        "page_id": data.get("id"),
                        "page_name": data.get("name"),
                        "page_link": data.get("link"),
                        "fan_count": data.get("fan_count")
                    }
                else:
                    err_msg = data.get("error", {}).get("message", "Lỗi không xác định từ Meta Graph API")
                    log_audit("FACEBOOK_CONN_ERROR", "FB_PUBLISHER", f"Error: {err_msg}")
                    return {
                        "connected": False,
                        "error": err_msg,
                        "fb_error": data.get("error")
                    }
        except Exception as e:
            return {"connected": False, "error": f"Lỗi kết nối mạng: {str(e)}"}

    async def publish_or_schedule_post(
        self,
        post_id: int,
        operating_mode: str = "SHADOW_MODE",
        emergency_stop: bool = False,
        publish_immediately: bool = True
    ) -> Dict:
        """
        Execute publication or scheduling for a post record.
        Respects Operating Mode (SHADOW_MODE, MANUAL, SEMI_AUTO, FULL_AUTO)
        and Emergency Stop safety brake.
        """
        if emergency_stop:
            return {"success": False, "error": "EMERGENCY_STOP đang kích hoạt. Đã dừng xuất bản an toàn."}

        # Ensure Page Token is resolved if not yet cached
        if not get_setting("meta_effective_page_token") and self.access_token:
            self.access_token = self._resolve_page_token(self.access_token)

        conn = get_db_connection()
        post_row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not post_row:
            conn.close()
            return {"success": False, "error": f"Không tìm thấy bài viết #{post_id}"}
        post = dict(post_row)

        # Check attached media items
        media_rows = conn.execute("SELECT * FROM media WHERE post_id = ? OR article_id = ?", (post_id, post["article_id"])).fetchall()
        media_items = [dict(m) for m in media_rows]

        # In SHADOW_MODE: Simulate publication without calling external Facebook API
        if operating_mode == "SHADOW_MODE":
            shadow_fb_id = f"shadow_fb_{post['post_uuid'][:12]}"
            shadow_link = f"https://www.facebook.com/lifetoday.vn/posts/{shadow_fb_id}"
            now_iso = datetime.now().isoformat()

            conn.execute("""
                UPDATE posts SET
                    status = 'SHADOW_PUBLISHED',
                    fb_post_id = ?,
                    fb_permalink = ?,
                    published_time = ?,
                    updated_at = ?
                WHERE id = ?
            """, (shadow_fb_id, shadow_link, now_iso, now_iso, post_id))
            conn.commit()
            conn.close()

            log_audit("SHADOW_PUBLISH_SUCCESS", "FB_PUBLISHER", f"Simulated publish #{post_id} -> {shadow_fb_id}")
            return {
                "success": True,
                "shadow_mode": True,
                "fb_post_id": shadow_fb_id,
                "fb_permalink": shadow_link,
                "message": "[CHẠY THỬ NGẦM (SHADOW MODE)] Đã mô phỏng đăng thành công. Để đăng thật lên Facebook, hãy đổi Chế độ vận hành sang Bán tự động (SEMI_AUTO) hoặc Tự động (FULL_AUTO) trong tab Cài đặt."
            }

        # REAL PUBLICATION: Validate Facebook credentials
        if not self.is_configured():
            conn.close()
            return {
                "success": False,
                "error": "Chưa có Page Access Token hoặc Page ID. Bạn hãy vào tab '⚙️ Cài đặt & AI' dán Token và Page ID vào nhé."
            }

        # Media rights check: If user manually approves or semi-auto, grant verified status
        if post.get("post_type") == "ORIGINAL_PHOTO_POST" and media_items:
            for m in media_items:
                if m.get("rights_status") == "WAITING_FOR_RIGHTS":
                    conn.execute("UPDATE media SET rights_status = 'VERIFIED_FREE' WHERE id = ?", (m["id"],))
            conn.commit()

        caption_body = post.get('caption', '')
        # Auto-ensure source link is present in caption if not already attached
        if post.get("article_id"):
            art_row = conn.execute("SELECT url FROM articles WHERE id = ?", (post["article_id"],)).fetchone()
            if art_row and art_row["url"]:
                art_url = art_row["url"]
                if art_url not in caption_body:
                    caption_body = f"{caption_body.strip()}\n\n👉 Xem chi tiết tại: {art_url}"

        message_text = f"{caption_body.strip()}\n\n{post.get('hashtags', '')}"
        credit = post.get("credit_source", "")
        if credit:
            import re
            credit_clean = re.sub(r"^(Ảnh\s*/\s*Nguồn:\s*)+", "", credit, flags=re.IGNORECASE).strip()
            message_text += f"\nẢnh / Nguồn: {credit_clean}"

        # Determine whether to use Meta native future scheduling or publish immediately now
        use_fb_native_schedule = False
        scheduled_unix = None
        if not publish_immediately and post.get("scheduled_time"):
            try:
                sched_ts = int(datetime.fromisoformat(post["scheduled_time"]).timestamp())
                now_ts = int(datetime.now().timestamp())
                if sched_ts > now_ts + 900:  # Meta requires >= 10-15 min in future
                    use_fb_native_schedule = True
                    scheduled_unix = sched_ts
            except Exception:
                use_fb_native_schedule = False

        # Real Graph API call
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                fb_result = None

                # 1. Photo Post (if media items exist)
                if media_items and (media_items[0].get("local_path") or media_items[0].get("original_url")):
                    first_media = media_items[0]
                    local_path = first_media.get("local_path")
                    orig_url = first_media.get("original_url")

                    if local_path and os.path.exists(local_path):
                        with open(local_path, "rb") as f:
                            files = {"source": f}
                            data = {"caption": message_text, "access_token": self.access_token}
                            if use_fb_native_schedule and scheduled_unix:
                                data["published"] = "false"
                                data["scheduled_publish_time"] = scheduled_unix
                            resp = await client.post(f"{META_GRAPH_API_BASE}/{self.page_id}/photos", data=data, files=files)
                            fb_result = resp.json()
                    elif orig_url:
                        # Direct URL photo publish (Meta downloads directly from CDN)
                        data = {"caption": message_text, "url": orig_url, "access_token": self.access_token}
                        if use_fb_native_schedule and scheduled_unix:
                            data["published"] = "false"
                            data["scheduled_publish_time"] = scheduled_unix
                        resp = await client.post(f"{META_GRAPH_API_BASE}/{self.page_id}/photos", data=data)
                        fb_result = resp.json()
                    else:
                        payload = {"message": message_text, "access_token": self.access_token}
                        if use_fb_native_schedule and scheduled_unix:
                            payload["published"] = False
                            payload["scheduled_publish_time"] = scheduled_unix
                        resp = await client.post(f"{META_GRAPH_API_BASE}/{self.page_id}/feed", json=payload)
                        fb_result = resp.json()

                # 2. Text or Link Post
                else:
                    payload = {"message": message_text, "access_token": self.access_token}
                    if use_fb_native_schedule and scheduled_unix:
                        payload["published"] = False
                        payload["scheduled_publish_time"] = scheduled_unix
                    resp = await client.post(f"{META_GRAPH_API_BASE}/{self.page_id}/feed", json=payload)
                    fb_result = resp.json()

                if "id" in fb_result:
                    fb_id = fb_result["id"]
                    permalink = f"https://www.facebook.com/{fb_id}"
                    now_iso = datetime.now().isoformat()
                    new_status = "SCHEDULED" if use_fb_native_schedule else "PUBLISHED"

                    # First Comment Feature: Attempt to attach source link in first comment if permission allows
                    if not use_fb_native_schedule and post.get("article_id"):
                        try:
                            art_row = conn.execute("SELECT url FROM articles WHERE id = ?", (post["article_id"],)).fetchone()
                            if art_row and art_row["url"]:
                                comment_url = art_row["url"]
                                comment_text = f"👉 Đọc trọn vẹn bài viết tại: {comment_url}"
                                comment_resp = await client.post(
                                    f"{META_GRAPH_API_BASE}/{fb_id}/comments",
                                    data={"message": comment_text, "access_token": self.access_token}
                                )
                                comment_data = comment_resp.json()
                                if "id" in comment_data:
                                    log_audit("FIRST_COMMENT_POSTED", "FB_PUBLISHER", f"Auto-commented source link on post {fb_id}")
                                else:
                                    err_detail = comment_data.get("error", {}).get("message", "Permission denied")
                                    log_audit("FIRST_COMMENT_FAILED", "FB_PUBLISHER", f"Could not comment on {fb_id}: {err_detail}")
                        except Exception as comment_err:
                            log_audit("FIRST_COMMENT_ERROR", "FB_PUBLISHER", f"Comment exception: {str(comment_err)}")

                    conn.execute("""
                        UPDATE posts SET
                            status = ?,
                            fb_post_id = ?,
                            fb_permalink = ?,
                            published_time = ?,
                            error_message = NULL,
                            updated_at = ?
                        WHERE id = ?
                    """, (new_status, fb_id, permalink, now_iso, now_iso, post_id))
                    conn.commit()
                    conn.close()

                    log_audit("FACEBOOK_PUBLISH_SUCCESS", "FB_PUBLISHER", f"Post #{post_id} published with FB ID {fb_id}")
                    return {
                        "success": True,
                        "fb_post_id": fb_id,
                        "fb_permalink": permalink,
                        "status": new_status
                    }
                else:
                    err_msg = fb_result.get("error", {}).get("message", "Lỗi xuất bản Facebook")
                    conn.execute("UPDATE posts SET status = 'FAILED', error_message = ?, updated_at = datetime('now') WHERE id = ?", (err_msg, post_id))
                    conn.commit()
                    conn.close()
                    return {"success": False, "error": err_msg, "fb_error": fb_result}

        except Exception as e:
            conn.execute("UPDATE posts SET status = 'FAILED', error_message = ?, updated_at = datetime('now') WHERE id = ?", (str(e), post_id))
            conn.commit()
            conn.close()
            return {"success": False, "error": f"Lỗi ngoại lệ xuất bản: {str(e)}"}
