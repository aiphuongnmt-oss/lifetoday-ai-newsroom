"""
Test Media Engine, Media Rights & Semantic Deduplication
"""
from PIL import Image, ImageDraw
import io
from backend.app.engines.media_engine import validate_image_bytes, compute_dhash
from backend.app.engines.media_rights import check_media_publishable
from backend.app.engines.deduplication import compute_title_similarity, hamming_distance

def test_media_validator():
    # Create test high-res image (1200x1600)
    img = Image.new("RGB", (1200, 1600), color=(240, 240, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle([200, 200, 1000, 1400], fill=(50, 100, 200), outline=(20, 20, 20), width=5)
    draw.text((300, 500), "LIFE TODAY EDITORIAL TEST", fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    data = buf.getvalue()

    metrics = validate_image_bytes(data)
    print(f"Validated Image Metrics: {metrics['width']}x{metrics['height']} | Format: {metrics['file_format']} | Sharpness: {metrics['sharpness_score']} | Status: {metrics['quality_status']}")
    assert metrics["is_valid"], "Image must be valid"
    assert metrics["quality_status"] == "QUALIFIED", "High-res image must be QUALIFIED"
    assert len(metrics["phash"]) > 0, "pHash must be computed"
    print("Media Validator Tests PASSED!")

def test_media_rights():
    item_unverified = {"quality_status": "QUALIFIED", "rights_status": "WAITING_FOR_RIGHTS"}
    publishable, reason = check_media_publishable(item_unverified)
    assert not publishable, "WAITING_FOR_RIGHTS must not be publishable"
    print(f"Correctly blocked: {reason}")

    item_verified = {"quality_status": "QUALIFIED", "rights_status": "PRESS_KIT"}
    publishable, reason = check_media_publishable(item_verified)
    assert publishable, "PRESS_KIT must be publishable"
    print("Media Rights Tests PASSED!")

def test_deduplication():
    t1 = "Địch Lệ Nhiệt Ba xuất hiện lộng lẫy tại thảm đỏ Cannes 2026"
    t2 = "Tại thảm đỏ Cannes 2026, Địch Lệ Nhiệt Ba xuất hiện vô cùng lộng lẫy"
    sim = compute_title_similarity(t1, t2)
    print(f"Title Similarity: {sim*100:.1f}%")
    assert sim >= 0.60, "Rewritten headline for same event must be identified as duplicate"

    # Perceptual hash hamming distance test
    h1 = "f0e1d2c3b4a59687"
    h2 = "f0e1d2c3b4a59687" # Identical
    assert hamming_distance(h1, h2) == 0

    h3 = "f0e1d2c3b4a59686" # 1 bit difference
    assert hamming_distance(h1, h3) == 1
    print("Deduplication Tests PASSED!")

if __name__ == "__main__":
    test_media_validator()
    test_media_rights()
    test_deduplication()
