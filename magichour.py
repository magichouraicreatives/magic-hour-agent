import glob
import os
from magic_hour import Client
from dotenv import load_dotenv

load_dotenv()

client = Client(token=os.getenv("MAGICHOUR_API_KEY"))

MODEL_DURATIONS = {
    "sora-2":    [4, 8, 12, 24, 36, 48, 60],
    "kling-3.0": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
}

CONTENT_TYPE_MODELS = {
    "pixar_dream_story": "sora-2",    # Mira's world stories — story-first
    "niche_story":       "sora-2",    # Wizard transformation — storytelling
    "flipped_meme":      "kling-3.0",
     "awe_clip":          "sora-2",
}
 
# Default durations per content type (snapped to nearest valid)
DEFAULT_DURATIONS = {
    "pixar_dream_story": 20,  # longer for emotional story arc
    "niche_story":       20,  # longer for transformation to breathe
    "flipped_meme":      12,
    "awe_clip":          4,  # shorter, punchy comedy
}

def _select_model(content_type: str) -> str:
    return CONTENT_TYPE_MODELS.get(content_type, "sora-2")

def _nearest_duration(target: int, model:str) -> int:
    valid = MODEL_DURATIONS.get(model, MODEL_DURATIONS["sora-2"])
    return float(min(valid, key=lambda x: abs(x - target)))

def generate_awe_image(image_prompt: str, title: str = "Awe Clip") -> dict:

    print(f"\nGenerating image...")
    print(f"Prompt: {image_prompt[:80]}...")

    try:
        result = client.v1.ai_image_editor.generate(
            assets={
            "image_file_paths": ["image1.png", "image2.png"]
            },
            image_count=1,   # 9:16 vertical
            style={
                "prompt": image_prompt,
                 #"tool": "ai-illustration-generator"
            },
            model="seedream-v4",
            name=title,
            wait_for_completion=True,
            download_outputs=True,
            download_directory="/tmp",
        )

        downloads = getattr(result, "downloads", []) or []
        image_url = None
        if downloads:
            image_url = downloads[0].url if hasattr(downloads[0], "url") else str(downloads[0])

        # Find downloaded image
        tmp_imgs = sorted(
            glob.glob("/tmp/*.jpg") + glob.glob("/tmp/*.png") + glob.glob("/tmp/*.webp"),
            key=os.path.getmtime, reverse=True
        )
        local_path = tmp_imgs[0] if tmp_imgs else None

        print(f"Image ready: {local_path}")
        return {
            "status": "complete",
            "image_url": image_url,
            "local_path": local_path,
            "credits_charged": getattr(result, "credits_charged", None),
        }

    except Exception as e:
        print(f" Image generation failed: {e}")
        return {"status": "failed", "error": str(e)}


def animate_image_to_video(image_url: str, motion_prompt: str,
                            title: str = "Awe Clip") -> dict:

    print(f"\nAnimating image to video...")
    print(f"Motion: {motion_prompt[:80]}...")

    try:
        result = client.v1.image_to_video.generate(
            end_seconds=4,
            resolution="720p",
            assets={
                "image_file_path": image_url
            },
            style={
                "prompt": motion_prompt,
            },
            name=title,
            wait_for_completion=True,
            download_outputs=True,
            download_directory="/tmp",
        )

        downloads = getattr(result, "downloads", []) or []
        video_url = None
        if downloads:
            video_url = downloads[0].url if hasattr(downloads[0], "url") else str(downloads[0])

        tmp_files = sorted(glob.glob("/tmp/*.mp4"), key=os.path.getmtime, reverse=True)
        local_path = tmp_files[0] if tmp_files else None

        print(f" Video ready: {local_path}")
        return {
            "status": "complete",
            "video_url": video_url,
            "local_path": local_path,
            "credits_charged": getattr(result, "credits_charged", None),
        }

    except Exception as e:
        print(f"Animation failed: {e}")
        return {"status": "failed", "error": str(e)}


def generate_awe_clip_video(prompt_package: dict) -> dict:
    image_prompt = prompt_package.get("image_prompt") or prompt_package.get("sora_prompt", "")
    motion_prompt = prompt_package.get("motion_prompt", "gentle slow camera push in, soft breeze, petals drifting, looping")
    title = prompt_package.get("visual_concept", "Awe Clip")[:50]

    # Step 1: Generate image
    image_result = generate_awe_image(image_prompt, title)
    if image_result.get("status") != "complete":
        return {"status": "failed", "error": f"Image gen failed: {image_result.get('error')}"}

    image_url = image_result.get("image_url")
    if not image_url:
        return {"status": "failed", "error": "No image URL returned"}

    # Step 2: Animate
    video_result = animate_image_to_video(image_url, motion_prompt, title)
    if video_result.get("status") != "complete":
        return {"status": "failed", "error": f"Animation failed: {video_result.get('error')}"}

    total_credits = (image_result.get("credits_charged") or 0) + (video_result.get("credits_charged") or 0)

    return {
        "status": "complete",
        "local_path": video_result.get("local_path"),
        "video_url": video_result.get("video_url"),
        "image_url": image_url,
        "image_path": image_result.get("local_path"),
        "credits_charged": total_credits,
        "content_type": "awe_clip",
    }

def generate_video(prompt_package):

    content_type = prompt_package.get("content_type", "pixar_dream_story")
    prompt = prompt_package.get("sora_prompt", "")
    model = _select_model(content_type)
    title = prompt_package.get("episode_title") or prompt_package.get("format_used") or "Magic Hour Agent"
    
    target_duration = prompt_package.get(
        "duration_seconds",
        DEFAULT_DURATIONS.get(content_type, 12)
    )
    duration = _nearest_duration(target_duration, model)

    print(f"Submitting video to Magic Hour: {prompt}")
    try:
        result = client.v1.text_to_video.generate(
            end_seconds=duration,
            orientation="portrait",
            resolution="720p",
            model=model,
            style={"prompt": prompt},
            name=title,
            audio=False,
            wait_for_completion=True,
            download_outputs=True,
            download_directory="/tmp"
        
        )

        downloads = getattr(result, "downloads", []) or []
        video_url = None

        if downloads:
            video_url = downloads[0].url if hasattr(downloads[0], "url") else str(downloads[0])

        import glob
        tmp_files = sorted(glob.glob("/tmp/*.mp4"), key=os.path.getmtime, reverse=True)
        local_path = tmp_files[0] if tmp_files else None

        if getattr(result, "credits_charged", None):
            print(f"   Credits used: {result.credits_charged}")

        print(f"Complete! file: {local_path}")

        return {
            "status": "complete",
            "video_url": video_url,
            "local_path": local_path,
            "model_used": model,
            "duration_seconds": duration,
            "prompt_package": prompt_package,
            "credits_charged": getattr(result, "credits_charged", None),
        }
    except Exception as e:
        print(f"Generation failed: {e}")
        return {"status": "failed", "error": str(e)}
    

def download_video(video_url: str, output_path:str) -> str:
    import requests
    print(f"Downloading from URl...")
    response = requests.get(video_url, stream=True, timeout=120)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = os.path.getsize(output_path)/ (1024*1024)
    print(f"Saved: {output_path} ({size_mb:.1f} MB)")
    return output_path
    
if __name__ == "__main__":
    test_package = {
        "sora_prompt": "A tired young woman in an oversized cream hoodie sits at a grey desk. "
                       "She notices a soft golden glow under a door that wasn't there before. "
                       "She opens it and steps into a vast ancient Egyptian city at golden hour — "
                       "warm sandstone temples, the Nile glittering, people in flowing robes. "
                       "She touches a glowing hieroglyph wall in pure wonder. Cinematic, emotional.",
        "duration_seconds": 12,
        "episode_title": "The Golden Door",
        "content_type": "escapist_story",
    }

    result = generate_video(test_package)
    print(f"Status: {result.get('status')}")
    print(f"File: {result.get('local_path')}")
