import json
from datetime import datetime
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def _call_gemini(prompt: str, label: str) -> list | dict:
    """Helper — calls Gemini and parses JSON response."""
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rstrip("`")
        return json.loads(text)
    except Exception as e:
        print(f"  ⚠️ {label} error: {e}")
        return []

def research_viral_worlds()-> list[dict]:
    print("Researching viral worlds...")
    return _call_gemini(f"""
    Search for visual world aesthetics and settings that are going viral on TikTok and Instagram 
short-form video RIGHT NOW (as of {datetime.utcnow().strftime('%B %Y')}).

I need worlds that:
1. Make viewers feel transported — "I wish I could be there"
2. Are visually stunning in a 15-25 second vertical video format
3. Are trending in AI art, fantasy, historical, or sci-fi content
4. Have a strong emotional quality (awe, wonder, longing, mystery)

For each world, give me enough visual detail to actually generate it with Sora AI:
- Specific lighting conditions
- Color palette
- Architectural or natural details
- Time of day / atmosphere
- What makes it feel alive and real, not just pretty

Return a JSON array of 8 worlds, each with:
{{
  "world_name": "evocative name",
  "visual_description": "rich detailed description for AI video generation",
  "lighting": "specific lighting details",
  "color_palette": "dominant colors",
  "emotional_quality": "what emotion this world triggers",
  "virality_signal": 1-10,
  "why_viewers_want_to_be_there": "one sentence on the visceral appeal",
  "trending_because": "why this aesthetic is hot right now"
}}

Return ONLY the JSON array.
""", "viral worlds")

    
def research_niche_communties() -> list[dict]:
    print("Researching niche communities...")
    return _call_gemini(f"""
    Search for specific professional and creative niche communities that are 
highly active and engaged on TikTok and Instagram RIGHT NOW ({datetime.utcnow().strftime('%B %Y')}).

I need niches where:
1. The community has strong shared identity (they're proud of what they do)
2. They're currently active/growing on social media
3. Content that speaks their language gets shared heavily within the community
4. They have a vivid "dream version" of their work that AI could visualize

Be specific - not "designers" but "brutalist architecture students" or 
"3D parametric modelers" or "deep sea coral researchers."

For each niche, I need enough to create a real video concept:
- What their ordinary work actually looks like (specific, authentic details)
- The exact transformation: what magical version of their work would they step into
- One insider detail only they would recognize (technical term, inside joke, shared frustration)
- Why this community would share the video

Return a JSON array of 6 niches, each with:
{{
  "niche": "specific community name",
  "real_work_scene": "what their ordinary work moment looks like visually",
  "dream_transformation": "the exact magical version they step into — detailed and visual",
  "insider_detail": "something only this community would recognize",
  "community_size": "estimate of social media following",
  "share_trigger": "why they'd share this with their community",
  "shareability": 1-10
}}

Return ONLY the JSON array.
""", "hot niches")


def research_story_formats() -> list[dict]:
    print("Reseearching story formats...")
    prompt = """
    Find short-form video story formats that are getting massive views on TikTok/Instagram.
    Examples of what I mean: animated animal stories, historical ship/disaster recreations,
    fantasy character journeys, "day in the life of" historical figures, or just cute cartoon animations.
    
    For each format:
    - What's the core story structure (setup → conflict → emotional peak → resolution)
    - What makes it emotionally transporting (viewer feels like they're there)
    - Visual style that works best for this format
    - Why viewers watch till the end
    - Typical view counts and engagement patterns
    - What niche or broad audience it appeals to
    
    Focus on formats where the viewer thinks "I wish I could be there" —
    that feeling of wanting to transport into the world.
    
    Return as JSON array with fields:
    format_name, story_structure, transport_mechanism, visual_style, 
    completion_rate_signal, audience_breadth, example_description
    
    Return ONLY the JSON array.
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f" Story format research error: {e}")
        return []
    
def research_meme_trends() -> list[dict]:
    print("Researching meme trends...")
    return _call_gemini(f"""
    Find viral short-form video text (TikTok/Instagram, {datetime.now().strftime('%B %Y')}).


    STYLE:

    * lowercase
    * short lines (3–8 words)
    * relatable, specific, human
    * mix: funny + painful + comforting

    FORMAT:
    Return JSON array of 12 items:
    {{
    "type": "pov and relatable ",
    "lines": ["line1","line2","line3","line4"],
    "visual_structure": "exact beat-by-beat structure to support the main text on the screen",
    "emotion": "short tag",
    "comedy_device": "what makes it funny or satisfying",
    "visual": "short visual idea"
    }}

    ---

    EXAMPLES (copy pattern, not exact words):

    {{
    "type":"inner_monologue",
    "lines":[
    "i have so much to do",
    "like actually too much",
    "so i’m taking a break first",
    "and now it’s been 3 hours"
    ],
    "emotion":"overwhelmed + avoidance",
    "visual":"girl staring at laptop, soft glow"
    }}

    {{
    "type":"relatable",
    "lines":[
    "opening canvas",
    "seeing 5 assignments",
    "closing canvas",
    "i’ll deal with it later"
    ],
    "emotion":"school stress",
    "visual":"screen light in dark room"
    }}

    {{
    "type":"pov",
    "lines":[
    "you finally start working",
    "you feel productive for once",
    "then one small mistake",
    "and now you hate everything"
    ],
    "emotion":"fragile motivation",
    "visual":"aesthetic desk, sudden glitch"
    }}

    {{
    "type":"inner_monologue",
    "lines":[
    "i’ll just rest for a bit",
    "i deserve it",
    "i needed that",
    "why do i feel worse"
    ],
    "emotion":"burnout",
    "visual":"sunset fade to night"
    }}

    {{
    "type":"relatable",
    "lines":[
    "rereading the same sentence",
    "again",
    "again",
    "still nothing"
    ],
    "emotion":"brain fog",
    "visual":"blurry book page"
    }}

    ---

    Generate NEW ones like above.

    RULES:

    * specific situations only
    * no generic motivation
    * must feel “this is literally me”
    * last line = payoff

    Return ONLY JSON.
    """, "meme trends")

def research_emotional_hooks() -> list[dict]:
        print("Researching dominant emotional hooks...")
        return _call_gemini(f"""
    Search for what emotional triggers are most effectively stopping scrolls and 
    driving shares on short-form video ({datetime.utcnow().strftime('%B %Y')}).

    Focus on emotions that produce VISCERAL reactions — not just "interesting" but
    emotions that make someone immediately share or rewatch.

    For each emotional hook:
    - What visual or story element triggers it
    - Why it's resonating specifically right now (cultural moment, season, etc.)
    - How to execute it in a 15-25 second vertical video
    - Which audience it hits hardest

    Return a JSON array of 5 emotional hooks, each with:
    {{
    "emotion": "specific emotion name",
    "trigger_element": "what visual or story element triggers it",
    "why_now": "why this is peaking right now",
    "visual_execution": "how to create this feeling in a short video",
    "target_audience": "who feels this most strongly",
    "virality_signal": 1-10
    }}

    Return ONLY the JSON array.
    """, "emotional hooks")

    
# def run_research():
#     print("\nResearch is running...")

#     viral_worlds = research_viral_worlds()
#     emotional_hooks = research_emotional_hooks()
#     niche_communities = research_niche_communties()
#     story_formats = research_story_formats()
#     meme_trends = research_meme_trends()

#     viral_worlds = sorted(viral_worlds, key=lambda x: x.get("virality_signal",0), reverse=True)[:5]
#     top_emotions = sorted(emotional_hooks, key=lambda x: x.get("virality_signal",0), reverse=True)[:5]
#     top_niches = sorted(niche_communities, key=lambda x: x.get("shareability",0), reverse=True)[:5]
#     top_stories = sorted(story_formats, key=lambda x: x.get("completion_rate_signal", 5), reverse=True)[:5]
#     top_memes = sorted(meme_trends, key=lambda x: x.get("virality_signal",0), reverse=True)[:5]

#     report = {
#         "timestamp": datetime.utcnow().isoformat(),
#         "viral_worlds": viral_worlds,
#         "top_emotional_hooks": top_emotions,
#         "top_niches": top_niches,
#         "top_story_formats": top_stories,
#         "top_meme_trends": top_memes,
#         "raw": {
#             "emotional_hooks": emotional_hooks,
#             "niche_communities": niche_communities,
#             "sory_formats": story_formats,
#             "meme_trends": meme_trends
#         },
#         "summary": {
#             "top_world": viral_worlds[0] if viral_worlds else None,
#             "dominant_emotion": top_emotions[0].get("emotion") if top_emotions else "awe",
#             "hottest_niche": top_niches[0].get("niche") if top_niches else "general",
#             "best_story_format": top_stories[0].get("format_name") if top_stories else "character journey",
#             "trending_meme": top_memes[0]. get("format_name") if top_memes else "expectation vs reality"
#         }
#     }

#     report_path = f"/tmp/research_report_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
#     with open(report_path, "w") as f:
#         json.dump(report, f, indent=1)

#     print(f"Research complete")
#     if viral_worlds:
#         print(f"Top world: {viral_worlds[0].get('world_name')}")
#     if top_niches:
#         print(f"Top niche: {top_niches[0].get('niche')}")
#     if top_memes:
#         print(f"Top meme format: {top_memes[0].get('format_name')}")
#     if top_emotions:
#         print(f"Dominant emotion: {top_emotions[0].get('emotion')}")
#     if top_stories:
#         print(f"Best story format: {top_stories[0].get('format_name')}")
#     print("viral_worlds raw:", viral_worlds)
#     print("story_formats raw:", story_formats) 

#     return report


def run_research() -> dict:
    """
    Smart research that adapts to what the generator actually needs.
    
    Priority:
    1. If user_prompt_generator.py exists and has a RESEARCH_NEEDS list,
       only research those specific things
    2. Otherwise run minimal useful research (worlds + memes only)
       instead of all 5 expensive calls
    """
    print("\nResearch running...")
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime('%B %Y')

    # Check if user generator declares what it needs
    research_needs = []
    if os.path.exists("user_prompt_generator.py"):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("upg", "user_prompt_generator.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            research_needs = getattr(mod, "RESEARCH_NEEDS", [])
        except Exception:
            pass

    # Default to minimal research if no specific needs declared
    if not research_needs:
        research_needs = ["viral_worlds", "meme_trends"]

    print(f"  Researching: {', '.join(research_needs)}")

    viral_worlds = []
    top_emotions = []
    top_niches = []
    top_stories = []
    top_memes = []

    if "viral_worlds" in research_needs:
        raw = _call_gemini(f"""
Find 5 visual world aesthetics going viral on TikTok/Instagram right now ({now}).
Worlds that make viewers feel "I wish I could be there."
Trending in AI art, fantasy, historical, or sci-fi short-form video.

Return ONLY a JSON array of 5 worlds:
{{
  "world_name": "name",
  "visual_description": "detailed description for Sora AI generation",
  "lighting": "specific lighting",
  "color_palette": "dominant colors",
  "emotional_quality": "emotion triggered",
  "virality_signal": 1-10,
  "why_viewers_want_to_be_there": "one sentence"
}}
""", "viral worlds")
        viral_worlds = sorted(raw or [], key=lambda x: float(x.get("virality_signal", 5) if str(x.get("virality_signal", 5)).replace('.','').isdigit() else 5), reverse=True)[:5]

    if "meme_trends" in research_needs:
        raw = _call_gemini(f"""
Find 5 proven viral meme/comedy video formats working on TikTok/Instagram right now ({now}).
Formats that work as VISUAL video content — not just text memes.
Focus on formats with mundane→magical contrast or satisfying visual reveals.

Return ONLY a JSON array of 5 formats:
{{
  "format_name": "name",
  "visual_structure": "beat-by-beat what viewer sees",
  "mundane_setup": "specific relatable opening",
  "magical_counterpart": "specific stunning visual counterpart",
  "comedy_device": "what makes it funny",
  "aesthetic_quality": "what makes it beautiful",
  "text_overlay_style": "how text appears",
  "virality_signal": 1-10
}}
""", "meme trends")
        top_memes = sorted(raw or [], key=lambda x: float(x.get("virality_signal", 5) if str(x.get("virality_signal", 5)).replace('.','').isdigit() else 5), reverse=True)[:5]

    if "emotional_hooks" in research_needs:
        raw = _call_gemini(f"""
Find 5 emotional triggers stopping scrolls on short-form video right now ({now}).
Return ONLY a JSON array:
{{
  "emotion": "name",
  "trigger_element": "what visual triggers it",
  "visual_execution": "how to create this in a short video",
  "virality_signal": 1-10
}}
""", "emotional hooks")
        top_emotions = sorted(raw or [], key=lambda x: float(x.get("virality_signal", 5) if str(x.get("virality_signal", 5)).replace('.','').isdigit() else 5), reverse=True)[:5]

    if "niches" in research_needs:
        raw = _call_gemini(f"""
Find 5 specific professional/creative communities highly active on TikTok/Instagram ({now}).
Communities with strong identity and a vivid "dream version" of their work AI could visualize.
Return ONLY a JSON array:
{{
  "niche": "specific community name",
  "real_work_scene": "what their ordinary work looks like",
  "dream_transformation": "magical version they'd step into",
  "insider_detail": "something only they'd recognize",
  "share_trigger": "why they'd share this",
  "shareability": 1-10
}}
""", "niches")
        top_niches = sorted(raw or [], key=lambda x: float(x.get("shareability", 5) if str(x.get("shareability", 5)).replace('.','').isdigit() else 5), reverse=True)[:5]

    if "story_formats" in research_needs:
        raw = _call_gemini(f"""
Find 5 short-form video story formats getting massive views on TikTok/Instagram ({now}).
Formats where viewer thinks "I wish I could be there."
Return ONLY a JSON array:
{{
  "format_name": "name",
  "story_structure": "setup → conflict → peak → resolution",
  "transport_mechanism": "why viewer feels they're there",
  "visual_style": "best visual style for this format",
  "completion_rate_signal": 1-10
}}
""", "story formats")
        top_stories = sorted(raw or [], key=lambda x: float(x.get("completion_rate_signal", 5) if str(x.get("completion_rate_signal", 5)).replace('.','').isdigit() else 5), reverse=True)[:5]

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "viral_worlds": viral_worlds,
        "top_emotional_hooks": top_emotions,
        "top_niches": top_niches,
        "top_story_formats": top_stories,
        "top_meme_trends": top_memes,
        "summary": {
            "top_world": viral_worlds[0] if viral_worlds else None,
            "dominant_emotion": top_emotions[0].get("emotion") if top_emotions else "awe",
            "hottest_niche": top_niches[0].get("niche") if top_niches else "general",
            "best_story_format": top_stories[0].get("format_name") if top_stories else "character journey",
            "trending_meme": top_memes[0].get("format_name") if top_memes else "expectation vs reality",
        }
    }

    report_path = f"/tmp/research_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Research complete — {len(viral_worlds)} worlds, {len(top_memes)} meme formats")
    return report

if __name__ == "__main__":
    report = run_research()
    print("\nSummary:")
    print(json.dumps(report['summary'], indent=2))
