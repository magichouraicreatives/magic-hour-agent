import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()

DESCRIPTION_FILE = "channel_description.json"
OUTPUT_FILE = "user_system_prompt.txt"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))


# ── Step 1: Collect what the user wants ──────────────────────────────────────

def collect_description() -> dict:
    print("""
╔══════════════════════════════════════════════════════╗
║        Magic Hour — Hyper-Tuned Prompt Engineer      ║
╚══════════════════════════════════════════════════════╝

Describe the content you want to make. Gemini will turn this
into an absolute visual blueprint for your video generator.
""")

    print("── What kind of videos do you want to make? ─────────────────────")
    print("Be specific: visual style, mood, colors, characters, pacing, and vibe.")
    print()
    print("Type your description (press Enter twice when done):")
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    content_description = "\n".join(lines).strip()

    print("\n── Describe your target Aesthetic / Examples ─────────────────────")
    print("What are the key signature elements of the videos you want to replicate?")
    print("e.g., 'Cinematic lighting, specific framing, camera loops, distinct text overlay type'")
    print()
    print("Type your style targets (press Enter twice when done):")
    style_lines = []
    while True:
        s_line = input()
        if s_line == "" and style_lines and style_lines[-1] == "":
            break
        style_lines.append(s_line)
    style_targets = "\n".join(style_lines).strip()

    print("\n── Paste example video URLs to reference (Enter twice to skip) ───")
    example_urls = []
    while True:
        url = input().strip()
        
        # If the user presses Enter on an empty line, stop the loop
        if url == "":
            break
            
        # Optional: Clean up trailing commas if you accidentally paste them
        if url.endswith(","):
            url = url[:-1].strip()
            
        example_urls.append(url)

    print("\n── Anything to AVOID? (or press Enter to skip) ───────────────────")
    avoid = input("> ").strip()

    description = {
        "content_description": content_description,
        "style_targets": style_targets,
        "example_urls": [u for u in example_urls if u],
        "avoid": avoid,
        "created_at": datetime.utcnow().isoformat(),
    }

    with open(DESCRIPTION_FILE, "w") as f:
        json.dump(description, f, indent=2)
    print(f"\nDescription saved to {DESCRIPTION_FILE}")
    return description


def load_description() -> dict:
    if not os.path.exists(DESCRIPTION_FILE):
        print(f"No saved description at {DESCRIPTION_FILE}. Run without --load first.")
        sys.exit(1)
    with open(DESCRIPTION_FILE) as f:
        return json.load(f)


# ── Step 2: Gemini writes the system prompt block ────────────────────────────

def build_system_prompt(description: dict) -> str:
    example_block = ""
    if description.get("example_urls"):
        example_block = (
            "\nReference Content Profiles to match:\n"
            + "\n".join(f"  - {u}" for u in description["example_urls"])
        )

    avoid_block = ""
    if description.get("avoid"):
        avoid_block = f"\nCRITICAL RESTRICTION - NEVER GENERATE OR INCLUDE: {description['avoid']}"

    # We use a highly structured instruction template to force Gemini to build an exact style guide
    meta_prompt = f"""
You are an expert Creative Director and Senior AI Prompt Engineer. Your task is to write a highly directive, fixed Creative Brief system instruction block. 

This brief will act as the master identity guide injected into a video generation pipeline. It must force the downstream AI to strictly create content matching the user's specific dream style, structural formatting pacing, and core thematic rules.

USER DESIGN SPECIFICATIONS:
Core Content Intent: {description['content_description']}
Aesthetic Targets & Rules: {description['style_targets']}{example_block}{avoid_block}

INSTRUCTIONS FOR THE CREATIVE BRIEF:
1. Establish a clear creative persona (e.g., "You are a master of [X] style...").
2. Define explicit visual rendering directives (specify typical camera work, pacing, color treatment, and atmosphere).
3. Enforce the direct formatting principles: tell the prompt writer how to handle text descriptions smoothly without breaking realism.
4. Output ONLY the explicit creative guidelines. Do NOT mention JSON formatting rules, coding parameters, markdown elements, or headers. Write this as a clean block of master text.

Write the creative identity brief now:
"""

    print("\nGenerating your tuned system prompt blueprint...")
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=meta_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        sys.exit(1)


# ── Step 3: Save and confirm ──────────────────────────────────────────────────

def save_system_prompt(prompt_text: str):
    header = (
        f"# user_system_prompt.txt\n"
        f"# Tuned creative engine configuration profile\n\n"
    )
    with open(OUTPUT_FILE, "w") as f:
        f.write(header + prompt_text)
    print(f"\nSaved to {OUTPUT_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(load_existing: bool = False):
    if load_existing:
        description = load_description()
        print(f"Loaded: {description['content_description'][:120]}...")
        confirm = input("Regenerate system prompt with this description? (y/n): ").strip().lower()
        if confirm != "y":
            sys.exit(0)
    else:
        description = collect_description()

    system_prompt = build_system_prompt(description)

    print("\n── Tuned System Brief Output Preview ─────────────────────────────")
    print(system_prompt[:800] + ("..." if len(system_prompt) > 800 else ""))

    confirm = input("\nCommit this tuning profile to your agent? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled. Tuning configuration not saved.")
        sys.exit(0)

    save_system_prompt(system_prompt)
    print("\nTuning applied completely. Run `python main.py --now --test` to verify your outputs!")


if __name__ == "__main__":
    run(load_existing="--load" in sys.argv)