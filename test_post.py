"""
Standalone test for Postiz posting — uses the EXACT same post_to_platform()
logic as main.py, but skips video generation and lets you point at a local
video file instead.

Usage:
    python test_post.py /path/to/your/video.mp4
    python test_post.py /path/to/your/video.mp4 --platform tiktok
"""

import argparse
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description="Test Postiz posting with a local video")
parser.add_argument("video_path", help="Path to a local video file to upload/post")
parser.add_argument("--platform", default=None,
                     help="Platform to post to (tiktok/instagram/youtube/x). "
                          "If omitted, posts to ALL platforms found in your channel env vars.")
args = parser.parse_args()


# ── Config straight from env, same names as your .env ──────────────────────
POSTIZ_URL = os.getenv("POSTIZ_URL", "").rstrip("/")
POSTIZ_API_KEY = os.getenv("POSTIZ_API_KEY", "")

POSTIZ_CHANNELS = {
    "tiktok": os.getenv("POSTIZ_CHANNEL_TIKTOK", ""),
    "instagram": os.getenv("POSTIZ_CHANNEL_INSTAGRAM", ""),
    "youtube": os.getenv("POSTIZ_CHANNEL_YOUTUBE", ""),
    "x": os.getenv("POSTIZ_CHANNEL_X", ""),
}

CHANNEL_NAME = os.getenv("CHANNEL_NAME", "Test Channel")


# ── Exact same post_to_platform() logic as main.py ──────────────────────────
def post_to_platform(platform: str, video_path: str, prompt_package: dict) -> dict:
    api_key = POSTIZ_API_KEY
    integration_id = POSTIZ_CHANNELS.get(platform)

    if not api_key:
        return {"status": "skipped", "reason": "no postiz api key"}
    if not integration_id:
        return {"status": "skipped", "reason": f"no integration id for {platform}"}

    if not video_path or not os.path.exists(video_path):
        return {"status": "failed", "error": f"Video file not found at path: {video_path}"}

    if os.path.getsize(video_path) < 100:
        return {"status": "failed", "error": "video file too small"}

    base = f"{POSTIZ_URL}/api/public/v1"
    headers = {"Authorization": api_key, "ngrok-skip-browser-warning": "true"}
    caption = prompt_package.get("caption", "")
    hashtags = " ".join(prompt_package.get("hashtags", []))
    full_caption = f"{caption}\n\n{hashtags}"

    print(f"   [{platform}] Uploading {video_path} ({os.path.getsize(video_path)} bytes) to {base}/upload ...")

    upload_data = None
    for attempt in range(3):
        try:
            t0 = time.time()
            with open(video_path, "rb") as f:
                resp = requests.post(
                    f"{base}/upload", headers=headers,
                    files={"file": (os.path.basename(video_path), f, "video/mp4")},
                    timeout=300,
                )
            print(f"   [{platform}] Upload attempt {attempt+1}: status={resp.status_code} "
                  f"elapsed={time.time()-t0:.1f}s content-type={resp.headers.get('content-type')}")
            if "text/html" in resp.headers.get("content-type", ""):
                print(f"   [{platform}] HTML body preview: {resp.text[:300]}")
                return {"status": "failed", "error": "HTML response — check POSTIZ_API_KEY and URL"}
            resp.raise_for_status()
            upload_data = resp.json()
            print(f"   [{platform}] Upload response: {upload_data}")
            break
        except Exception as e:
            print(f"   [{platform}] Upload attempt {attempt+1} error: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                return {"status": "failed", "error": str(e)}

    if not upload_data:
        return {"status": "failed", "error": "upload failed after 3 attempts"}

    media_path = upload_data.get("path") or upload_data.get("url")
    media_id = upload_data.get("id")

    def _settings(p):
        if p == "tiktok":
            return {"__type": "tiktok", "privacy_level": "SELF_ONLY", "duet": False,
                    "stitch": False, "comment": True, "autoAddMusic": "no",
                    "brand_content_toggle": False, "brand_organic_toggle": False,
                    "content_posting_method": "DIRECT_POST"}
        if p == "instagram":
            return {"__type": "instagram-standalone", "post_type": "post"}
        if p == "youtube":
            title = prompt_package.get("episode_title") or CHANNEL_NAME
            return {"__type": "youtube", "title": title, "type": "public",
                    "selfDeclaredMadeForKids": "no"}
        if p == "x":
            return {"__type": "x", "who_can_reply_post": "everyone"}
        return {"__type": p}

    post_body = {
        "type": "now",
        "date": datetime.now(timezone.utc).isoformat().replace("+00:00", ".000Z"),
        "shortLink": False,
        "tags": [],
        "posts": [{
            "integration": {"id": integration_id},
            "value": [{"content": full_caption,
                        "image": [{"id": media_id, "path": media_path}]}],
            "settings": _settings(platform),
        }],
    }

    print(f"   [{platform}] Posting to {base}/posts ...")
    try:
        t0 = time.time()
        post_resp = requests.post(
            f"{base}/posts",
            headers={**headers, "Content-Type": "application/json"},
            json=post_body,
            timeout=30,
        )
        print(f"   [{platform}] Post response: status={post_resp.status_code} elapsed={time.time()-t0:.1f}s")
        print(f"   [{platform}] Body: {post_resp.text[:1000]}")
        post_resp.raise_for_status()
        data = post_resp.json()
        post_id = data[0].get("postId") if isinstance(data, list) else str(data)
        print(f"   Posted to {platform}: {post_id}")
        return {"platform": platform, "status": "posted", "post_id": post_id}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def main():
    video_path = args.video_path
    if not os.path.exists(video_path):
        raise SystemExit(f"Video not found at: {video_path}")

    print("=" * 60)
    print("POSTIZ POST TEST (using main.py logic)")
    print("=" * 60)
    print(f"POSTIZ_URL:     {POSTIZ_URL!r}")
    print(f"API_KEY set:    {bool(POSTIZ_API_KEY)} (len={len(POSTIZ_API_KEY)})")
    print(f"Video path:     {video_path}")
    print(f"Video size:     {os.path.getsize(video_path)} bytes")
    print("=" * 60)

    if args.platform:
        platforms = [args.platform]
    else:
        platforms = [p for p, cid in POSTIZ_CHANNELS.items() if cid]
        if not platforms:
            raise SystemExit("No POSTIZ_CHANNEL_* env vars are set — nothing to test.")

    print(f"Testing platforms: {platforms}\n")

    prompt_package = {
        "caption": "Test post from test_post.py",
        "hashtags": ["#test"],
        "episode_title": "Test Episode",
    }

    results = []
    for platform in platforms:
        print(f"\n--- {platform} ---")
        result = post_to_platform(platform, video_path, prompt_package)
        print(f"--- {platform} result: {result} ---")
        results.append(result)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        print(r)


if __name__ == "__main__":
    main()