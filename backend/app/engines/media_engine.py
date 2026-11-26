"""
LIFE TODAY — AI NEWSROOM V1.0
Original HD Media Engine & Pillow Quality Validator
"""
import hashlib
import io
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import httpx
import numpy as np
from PIL import Image, ImageStat

from backend.app.config import MEDIA_DIR
from backend.app.database import get_db_connection, log_audit

def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of image binary data."""
    return hashlib.sha256(data).hexdigest()

def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """
    Compute difference perceptual hash (dHash).
    Fast, reliable, and invariant to scaling and minor compression.
    """
    # Convert to grayscale and resize to (hash_size + 1, hash_size)
    img_gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(img_gray.getdata())

    # Compare adjacent pixels
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(pixel_left > pixel_right)

    # Convert binary list to hex string
    decimal_val = 0
    hex_str = []
    for idx, val in enumerate(difference):
        if val:
            decimal_val += 2 ** (idx % 4)
        if (idx % 4) == 3:
            hex_str.append(hex(decimal_val)[2:])
            decimal_val = 0
    return "".join(hex_str)

def compute_sharpness_score(image: Image.Image) -> float:
    """
    Compute sharpness score using gradient variance (Laplacian proxy).
    Higher score indicates sharper visual details. Blurry images score low (< 100).
    """
    try:
        gray = image.convert("L")
        arr = np.array(gray, dtype=np.float32)
        # Compute horizontal and vertical gradients
        gx = np.diff(arr, axis=1)
        gy = np.diff(arr, axis=0)
        # Variance of gradient magnitude
        variance = float(np.var(gx) + np.var(gy))
        return round(variance, 2)
    except Exception:
        # Fallback using standard deviation of image
        stat = ImageStat.Stat(image.convert("L"))
        return round(stat.stddev[0] ** 2, 2)

def validate_image_bytes(data: bytes) -> Dict:
    """
    Validate image file using Pillow:
    - Dimensions (width, height, aspect ratio)
    - Format (JPEG, PNG, WEBP)
    - File size
    - Sharpness score
    - SHA256 & dHash
    - Quality status (QUALIFIED, LOW_RES, BLURRY, CORRUPTED)
    """
    try:
        img = Image.open(io.BytesIO(data))
        img.verify() # Verify file integrity
        # Re-open for measurements because verify() invalidates the image pointer
        img = Image.open(io.BytesIO(data))

        width, height = img.size
        aspect_ratio = round(width / max(height, 1), 2)
        fmt = img.format or "JPEG"
        file_size = len(data)
        sha256 = compute_sha256(data)
        dhash = compute_dhash(img)
        sharpness = compute_sharpness_score(img)

        short_edge = min(width, height)
        long_edge = max(width, height)

        # Quality criteria
        # Preferred: short_edge >= 1080, long_edge >= 2000
        # Minimum acceptable for verified press: short_edge >= 720
        if short_edge < 720 or file_size < 50_000:
            quality_status = "LOW_RES"
        elif sharpness < 40.0: # Below blur threshold
            quality_status = "BLURRY"
        else:
            quality_status = "QUALIFIED"

        return {
            "is_valid": True,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "file_format": fmt,
            "file_size_bytes": file_size,
            "sharpness_score": sharpness,
            "sha256": sha256,
            "phash": dhash,
            "quality_status": quality_status,
            "image_obj": img
        }
    except Exception as e:
        return {
            "is_valid": False,
            "error": str(e),
            "quality_status": "CORRUPTED"
        }

async def download_and_validate_media(
    image_url: str,
    article_id: Optional[int] = None,
    rights_source: str = ""
) -> Optional[Dict]:
    """
    Download image from official URL, validate with Pillow, save to local media store,
    and update the SQLite database.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 LifeTodayMediaBot/1.0"
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(image_url)
            if resp.status_code != 200:
                return None

            data = resp.content
            metrics = validate_image_bytes(data)
            if not metrics["is_valid"]:
                return None

            # Generate local filename based on SHA256
            ext = metrics["file_format"].lower()
            if ext == "jpeg":
                ext = "jpg"
            filename = f"{metrics['sha256']}.{ext}"
            local_filepath = MEDIA_DIR / filename

            # Save locally
            with open(local_filepath, "wb") as f:
                f.write(data)

            media_uuid = hashlib.sha256(f"{article_id}|{image_url}".encode()).hexdigest()

            # Record in DB
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO media (
                    media_uuid, article_id, original_url, local_path, file_format,
                    width, height, aspect_ratio, file_size_bytes, sharpness_score,
                    sha256, phash, quality_status, rights_status, rights_source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'WAITING_FOR_RIGHTS', ?, datetime('now'))
                ON CONFLICT(media_uuid) DO UPDATE SET
                    local_path = excluded.local_path,
                    width = excluded.width,
                    height = excluded.height,
                    aspect_ratio = excluded.aspect_ratio,
                    file_size_bytes = excluded.file_size_bytes,
                    sharpness_score = excluded.sharpness_score,
                    sha256 = excluded.sha256,
                    phash = excluded.phash,
                    quality_status = excluded.quality_status
            """, (
                media_uuid, article_id, image_url, str(local_filepath),
                metrics["file_format"], metrics["width"], metrics["height"],
                metrics["aspect_ratio"], metrics["file_size_bytes"],
                metrics["sharpness_score"], metrics["sha256"], metrics["phash"],
                metrics["quality_status"], rights_source
            ))
            conn.commit()
            conn.close()

            log_audit("MEDIA_DOWNLOAD_VALIDATE", "MEDIA_ENGINE", f"Saved {filename} | {metrics['width']}x{metrics['height']} | Status: {metrics['quality_status']}")
            return {
                "media_uuid": media_uuid,
                "local_path": str(local_filepath),
                "metrics": metrics
            }
    except Exception as e:
        print(f"Error downloading media from {image_url}: {e}")
        return None
