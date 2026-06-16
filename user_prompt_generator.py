import json
import os
import sys
from dotenv import load_dotenv
from google import genai

load_dotenv()

SYSTEM_PROMPT_FILE = "user_system_prompt.txt"

# Module-level client — not recreated on every call
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))


def _call_gemini(prompt_text: str) -> dict:
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
        )
        text = response.text.strip()
        # Strip markdown fences if Gemini wraps the JSON anyway
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rstrip("`").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {}


def generate_prompt(research_report: dict = None) -> dict:
    """
    Reads the creative brief from user_system_prompt.txt, injects current
    trend research, and returns a structured video prompt package.
    Called by main.py on every scheduled slot.
    """
    if not os.path.exists(SYSTEM_PROMPT_FILE):
        print(f"ERROR: '{SYSTEM_PROMPT_FILE}' not found.")
        print("Run `python prompt_engineer.py` first to generate your creative brief.")
        return {}

    with open(SYSTEM_PROMPT_FILE, "r") as f:
        creative_brief = f.read()

    # Inject live trend data from scraper if available
    research_context = ""
    if research_report:
        top_niches = research_report.get("top_niches", [])
        viral_worlds = research_report.get("viral_worlds", [])
        top_emotions = research_report.get("top_emotional_hooks", [])
        research_context = f"""

CURRENT TRENDING CONTEXT (use this to keep content fresh and timely):
Top viral worlds: {[w.get("world_name") for w in viral_worlds[:3]]}
Top niches: {[n.get("niche") for n in top_niches[:3]]}
Dominant emotions: {[e.get("emotion") for e in top_emotions[:2]]}
"""

    output_format = """

---
Return ONLY valid JSON matching this exact schema — no markdown, no extra keys:
{
    "sora_prompt": "Physically descriptive prompt for an AI video model. Exact actions, subjects, colors, lighting, framing. Max 60 words.",
    "motion_prompt": "4-9 second seamless loop instructions. Gentle loopable motion only — drifting, swaying, flickering. Max 40 words.",
    "visual_concept": "One sentence capturing the core creative theme.",
    "caption": "Short scroll-stopping social caption. Under 10 words.",
    "hashtags": ["#relevant", "#hashtags", "#here"],
    "hook": "Under 5 words to grab attention.",
    "duration_seconds": 9,
    "content_type": "custom"
}
"""

    final_prompt = creative_brief + research_context + output_format

    print("Generating prompt from your creative brief...")
    result = _call_gemini(final_prompt)

    if result:
        result["content_type"] = result.get("content_type", "custom")
        result.setdefault("duration_seconds", 9)
        print(f"Done: {result.get('visual_concept', '')[:80]}")

    return result