import argparse
import glob
import importlib
import importlib.util
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone

import requests
import schedule
from dotenv import load_dotenv

load_dotenv()

# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Magic Hour Agent")
parser.add_argument("--config", default="channel_config.yaml")
parser.add_argument("--test", action="store_true")
parser.add_argument("--now", action="store_true")
args = parser.parse_args()

from config_loader import ChannelConfig
cfg = ChannelConfig(args.config)
if args.test:
    cfg.test_mode = True

from scraper import run_research
from magichour import generate_awe_clip_video, generate_video, download_video
from pinecone_store import store_video_performance


# ── Prompt generator routing ──────
def _load_user_generator():
    if os.path.exists("user_prompt_generator.py"):
        try:
            spec = importlib.util.spec_from_file_location("user_prompt_generator", "user_prompt_generator.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, "generate_prompt", None)
            if fn:
                print("Using your custom prompt generator (user_prompt_generator.py)")
                return fn
        except Exception as e:
            print(f"Could not load user_prompt_generator.py: {e}")
    return None


def get_prompt_generator():
    """Returns a callable: generate_prompt(research_report) -> dict"""
    user_gen = _load_user_generator()
    if user_gen:
        return user_gen

    print("No custom generator found — using preset generators.")
    print("Run `python prompt_engineer.py` to create your own.")
    from generator import (
        generate_awe_clip, generate_pixar_dream_story,
        generate_flipped_meme, generate_niche_story,
    )

    content_type = cfg.content_types[0] if cfg.content_types else "awe_clip"
    preset_map = {
        "awe_clip": generate_awe_clip,
        "pixar_dream_story": generate_pixar_dream_story,
        "flipped_meme": generate_flipped_meme,
        "niche_story": generate_niche_story,
    }
    return preset_map.get(content_type, generate_awe_clip)


# ── Research cache ───────────

PERSISTENT_DIR = "/data"

def get_research() -> dict:
    """
    Attempts to read cached research from the Railway volume.
    Falls back to running a fresh scrape if cache is expired or missing.
    """
    cache_hours = cfg.research_cache_hours
    
    # Check the persistent directory path instead of /tmp
    search_pattern = os.path.join(PERSISTENT_DIR, "research_report_*.json")
    reports = sorted(glob.glob(search_pattern), reverse=True)
    
    if reports:
        age = time.time() - os.path.getmtime(reports[0])
        if age < cache_hours * 3600:
            print(f"Using cached research ({int(age/3600)}h old)")
            with open(reports[0]) as f:
                return json.load(f)
                
    print("Running fresh research...")
    return run_research()

# ── Discord ─────────

def notify_discord(message: str, video_path: str = None):
    webhook_url = cfg.discord_webhook
    if not webhook_url:
        print(f"[notify] {message}")
        return
    try:
        if video_path and os.path.exists(video_path):
            with open(video_path, "rb") as f:
                requests.post(webhook_url, data={"content": message},
                              files={"file": f}, timeout=30)
        else:
            requests.post(webhook_url, json={"content": message}, timeout=10)
    except Exception as e:
        print(f"Discord error: {e}")


# ── Posting ────────────
def post_to_platform(platform: str, video_path: str, prompt_package: dict) -> dict:
    api_key = cfg.postiz_api_key
    integration_id = cfg.postiz_channels.get(platform)

    if not api_key:
        return {"status": "skipped", "reason": "no postiz api key"}
    if not integration_id:
        return {"status": "skipped", "reason": f"no integration id for {platform}"}

    if not video_path or not os.path.exists(video_path):
        return {"status": "failed", "error": f"Video file not found at path: {video_path}"}

    if os.path.getsize(video_path) < 100:
        return {"status": "failed", "error": "video file too small"}

    base = f"{cfg.postiz_url}/api/public/v1"
    headers = {"Authorization": api_key, "ngrok-skip-browser-warning": "true"}
    caption = prompt_package.get("caption", "")
    hashtags = " ".join(prompt_package.get("hashtags", []))
    full_caption = f"{caption}\n\n{hashtags}"

    upload_data = None
    for attempt in range(3):
        try:
            with open(video_path, "rb") as f:
                resp = requests.post(
                    f"{base}/upload", headers=headers,
                    files={"file": (os.path.basename(video_path), f, "video/mp4")},
                    timeout=300,
                )
            if "text/html" in resp.headers.get("content-type", ""):
                return {"status": "failed", "error": "HTML response — check POSTIZ_API_KEY and URL"}
            resp.raise_for_status()
            upload_data = resp.json()
            break
        except Exception as e:
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
            title = prompt_package.get("episode_title") or cfg.channel_name
            return {"__type": "youtube", "title": title, "type": "public",
                    "selfDeclaredMadeForKids": "no"}
        if p == "x":
            return {"__type": "x", "who_can_reply_post": "everyone"}
        return {"__type": p}

    post_body = {
        "type": "now",
        # FIXED: Swapped deprecated utcnow() for a clean, explicit ISO UTC timestamp string
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

    try:
        post_resp = requests.post(
            f"{base}/posts",
            headers={**headers, "Content-Type": "application/json"},
            json=post_body, 
            timeout=30,
        )
        post_resp.raise_for_status()
        data = post_resp.json()
        post_id = data[0].get("postId") if isinstance(data, list) else str(data)
        print(f"   Posted to {platform}: {post_id}")
        return {"platform": platform, "status": "posted", "post_id": post_id}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ── Core slot runner ───────────

def run_single_slot(prompt_package: dict):
    content_type = prompt_package.get("content_type", "custom")
 
    notify_discord(
        f"[{cfg.channel_name}] Generating {content_type}\n"
        f"Hook: {prompt_package.get('hook')}"
    )
 
    if cfg.test_mode:
        print("\n[TEST MODE] Skipping Magic Hour — using dummy video")
        dummy_path = f"/tmp/test_{content_type}.mp4"
        with open(dummy_path, "wb") as f:
            f.write(bytes.fromhex("0000001C667479706973736F6D") + b"\x00" * 1000)
        video_path = dummy_path
    else:
        result = (generate_awe_clip_video(prompt_package)
                  if content_type == "awe_clip"
                  else generate_video(prompt_package))
 
        if result.get("status") != "complete":
            notify_discord(f"Generation failed: {result.get('error')}")
            return None
 
        video_path = result.get("local_path")
        if not video_path and result.get("video_url"):
            video_path = f"/tmp/video_{content_type}_{int(time.time())}.mp4"
            download_video(result["video_url"], video_path)
 
    print(f"\nVideo ready: {video_path}")
 
    post_results = []
    for platform in cfg.platforms:
        post_results.append(post_to_platform(platform, video_path, prompt_package))
 
    successes = [r.get("platform") for r in post_results if r.get("status") == "posted"]
    notify_discord(
        f"[{cfg.channel_name}] Posted {content_type} — {', '.join(successes) or 'none'}",
        video_path=video_path,
    )
 
    store_video_performance({
        "prompt": prompt_package.get("sora_prompt"),
        "caption": prompt_package.get("caption"),
        "platform": cfg.platforms[0] if cfg.platforms else "unknown",
        "account": cfg.channel_name,
        "niche": cfg.niche,
        "content_type": content_type,
        "metrics": {"views": 0, "profile_visits": 0, "follows": 0},
        "posted_at": datetime.utcnow().isoformat(),
    })
 
    # Run analyzer every 5 posts to auto-improve the creative brief
    _maybe_run_analyzer()
 
    return post_results
 
 
_post_count_file = "/tmp/magichour_post_count.txt"
 
def _maybe_run_analyzer():
    """Increments post count and triggers analyzer every 5 posts."""
    try:
        count = 0
        if os.path.exists(_post_count_file):
            with open(_post_count_file) as f:
                count = int(f.read().strip() or 0)
        count += 1
        with open(_post_count_file, "w") as f:
            f.write(str(count))
        if count % 5 == 0:
            print(f"\nPost #{count} — running performance analysis...")
            try:
                from analyzer import run as run_analysis
                run_analysis(report_only=False, force_rewrite=False)
            except Exception as e:
                print(f"Analyzer error (non-fatal): {e}")
    except Exception:
        pass  # never block posting due to analyzer issues
 


# ── Scheduler ──────────────
def run_scheduled_slot(research: dict, generate_fn):
    print(f"\n{'='*50}")
    print(f"Scheduled slot at {datetime.now().strftime('%H:%M')}")
    prompt_package = generate_fn(research)
    if prompt_package:
        run_single_slot(prompt_package)


def main():
    print(f"\n{'='*55}")
    print(f"  Magic Hour Agent — {cfg.channel_name}")
    print(f"  Config: {args.config}")
    print(f"  Platforms: {', '.join(cfg.platforms)}")
    print(f"  Test mode: {cfg.test_mode}")
    print(f"{'='*55}\n")

    for w in cfg.validate():
        print(f"WARNING: {w}")

    research = get_research()
    generate_fn = get_prompt_generator()

    if args.now:
        print("\nRunning immediately (--now)...")
        prompt_package = generate_fn(research)
        if not prompt_package:
            print("Generation failed.")
            sys.exit(1)
        print(f"\nHook:    {prompt_package.get('hook')}")
        print(f"Caption: {prompt_package.get('caption')}")
        print(f"\nPrompt:\n{prompt_package.get('sora_prompt', '')[:300]}...")
        #confirm = input("\nPost this? (y/n): ").strip().lower()
        #if confirm == "y":
        run_single_slot(prompt_package)
        return

    for slot in cfg.schedule:
        schedule.every().day.at(slot["time"]).do(
            run_scheduled_slot, research, generate_fn
        )
        print(f"  Scheduled {slot['time']}")

    notify_discord(
        f"Scheduler started - {cfg.channel_name}\n"
        + "\n".join(f"  {s['time']}" for s in cfg.schedule)
    )

    print("\nWaiting for next slot...\n")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()