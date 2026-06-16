import json
import os
import random
from dotenv import load_dotenv
from pinecone_store import get_best_performing_content, get_character_description, get_recent_content, store_generated_content
from scraper import run_research
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROVEN_VIRAL_FORMATS = [
    {
        "name": "the_unspoken_rule",
        "structure": "Text overlay stating a highly specific, universally understood 'unspoken rule' or anxiety + a dramatic, mismatched visual reaction.",
        "why_works": "Extreme relatability causes viewers to immediately share it to their group chats or tag friends saying 'literally you'.",
        "example": "Text: 'Me trying to look casual walking past a cop even though I've never committed a crime in my life' → Visual: A hyper-realistic penguin stiffly marching in a tuxedo.",
    },
    {
        "name": "the_bait_and_switch_loop",
        "structure": "Starts with a highly engaging, seemingly serious setup that abruptly cuts to a completely unrelated, chaotic, or absurd punchline in under 3 seconds.",
        "why_works": "Triggers high watch time and immediate rewatches because the transition happens so fast the brain has to process it twice.",
        "example": "Text: '3 steps to completely fix your sleep schedule:' → Quick cut at 2 seconds to a wizard aggressively casting a spell on a clock.",
    },
    {
        "name": "me_explaining_to_my_cat",
        "structure": "A split-screen or quick cut between someone delivering a passionately complex, unhinged explanation and a completely blank, unbothered entity listening.",
        "why_works": "Plays on the popular 'no thoughts, head empty' humor style. Great for inserting niche community inside jokes.",
        "example": "Left side: Intense, fast-paced text about corporate drama. Right side: A tiny, AI-generated hamster just blinking slowly while wearing a tiny business tie.",
    },
    {
        "name": "historical_or_grand_scale_pettiness",
        "structure": "Using a grand, cinematic, or epic visual setting to describe a completely minor, petty, or everyday inconvenience.",
        "why_works": "The sheer contrast between the epic scale of the video and the triviality of the text creates instant comedic value.",
        "example": "Visual: An epic, slow-motion battle of knights in a thunderstorm. Text: 'My immune system fighting off the slight breeze because I slept with the window open.'",
    },
    {
        "name": "pov_you_said_the_wrong_thing",
        "structure": "First-person perspective where an entire room, crowd, or group of characters simultaneously freezes and stares directly into the camera with absolute judgment.",
        "why_works": "Creates an immediate, funny tension. Viewers flood the comments arguing about or defending the 'unpopular opinion' in the text.",
        "example": "Text: 'POV: You accidentally say \"I actually like working on Mondays\" in the breakroom' → Visual: A group of Renaissance-style painted characters slowly turning their heads to glare at the viewer.",
    },
    {
        "name": "the_overly_dramatic_exit",
        "structure": "A character or object leaving a situation with an entirely unnecessary level of flair, speed, or dramatic effect the second a mild inconvenience occurs.",
        "why_works": "Captures the internet's love for 'cancel culture' applied to minor daily social interactions.",
        "example": "Text: 'When the social battery hits 0% at the party' → Visual: A character instantly dissolving into a flock of dramatic crows and flying out the window.",
    },
    # --- NEW GEN Z & TALKING CAT VIRAL FORMATS ---
    {
        "name": "corporate_slang_vs_real_life",
        "structure": "Juxtaposing professional corporate terminology or toxic positivity over an aggressively chaotic, low-stakes visual, or vice versa.",
        "why_works": "Capitalizes on Gen Z's absolute disdain for corporate life and love for weaponizing HR-speak in casual scenarios.",
        "example": "Text: 'Per my last email (I am sending positive vibes)' → Visual: An orange cat sitting at a desk aggressively slapping a keyboard with steam coming out of its ears.",
    },
    {
        "name": "the_unhinged_talking_pet_confession",
        "structure": "A close-up shot of an animal looking directly into the camera, with its mouth moving seamlessly via AI, delivering a highly judgmental, existential, or sassy monologue using heavy internet slang.",
        "why_works": "Talking animals have an insanely high baseline engagement hook. Combining the cute visual with unhinged, self-aware Gen Z dialogue makes it instantly viral.",
        "example": "Visual: An ultra-realistic fluffy cat talking with human expressions. Text/Audio: 'You've been doomscrolling for 2 hours. Go look at a tree. I am literally begging you, the vibe is rancid right now.'",
    },
    {
        "name": "side_eye_judgment_council",
        "structure": "An assembly of unexpected characters (animals, historical figures, or fantasy creatures) slowly delivering the ultimate 'bombastic side-eye' to the viewer over a specific relatable failure.",
        "why_works": "Directly taps into active meme trends. The visual humor is entirely driven by the character expressions, causing people to spam the comment section.",
        "example": "Text: 'When you say you have no money but your third package of the week just arrived' → Visual: A row of three owls and a raccoon slowly turning their heads simultaneously to look at the camera with pure disappointment.",
    },
    {
        "name": "let_him_cook_delusion",
        "structure": "A character is doing something completely wrong, chaotic, or disastrous, but the text overlay and atmosphere treat them like an absolute mastermind who is 'cooking' a masterpiece.",
        "why_works": "Taps directly into slang ('let him cook', 'he is him', 'standing on business') used ironically to hype up absolute failure.",
        "example": "Text: 'My last remaining brain cell trying to solve a basic math problem at 3 AM' → Visual: A tiny kitten wearing safety goggles frantically pouring glowing liquids into beakers in a chaotic wizard lab while explosions happen behind it.",
    }
]

AWE_CLIP_SCENES = [
    # Nature/Garden/Rainforest
    "a magical rainforest waterfall with glowing bioluminescent flowers cascading down mossy rocks, soft golden mist rising",
    "an enchanted garden at dawn, giant luminous flowers slowly blooming, dewdrops falling in slow motion, soft pink light",
    "a secret forest clearing where thousands of fireflies drift upward through cherry blossom petals falling like snow",
    "an underwater garden of colorful coral and anemones swaying gently, rays of turquoise light filtering from above",
    "a mystical meadow of oversized glowing mushrooms and wildflowers under a full moon, soft purple and gold light",
    "ancient stone ruins completely consumed by lush tropical vines and blooming flowers, warm golden hour light",
    "a floating island covered in endless wildflowers drifting slowly through soft clouds at sunset, petals trailing behind",
    "a crystalline cave filled with giant luminescent flowers and dripping water catching rainbow light",
    "a Japanese zen garden at cherry blossom peak, petals drifting in slow spirals over still water",
    "a magical greenhouse with impossible flowers of every color, butterflies and light beams crossing slowly",

    # Mythical Beast Arrival
    "a hyper-realistic crystal dragon cutting through neon-pink storm clouds, its wings sending electric ripples across the sky",
    "a massive luminescent whale breaching through clouds above a sunset ocean, trailing waterfalls of golden light",

    # Surreal Macro Loop
    "a miniature floating water kingdom trapped inside a single spinning dewdrop, reflecting a brilliant golden-hour horizon",
    "an entire tiny forest ecosystem living inside a glass sphere, slowly rotating in warm afternoon light",

    # Bioluminescent Abyss
    "an ultra-realistic crystal jellyfish pulsing with iridescent teal light gliding upward, leaving a trail of glowing stardust",
    "a deep ocean cavern erupting with bioluminescent creatures suddenly lighting up in waves of neon blue and green",

    # Celestial Shatter
    "a massive ringed planet shattering into a million glowing purple particles that seamlessly swirl back into a solid sphere",
    "a full moon cracking open slowly, golden light pouring out through the fractures into a dark sky",

    # Enchanted Weather Surge
    "cherry blossom trees bursting into full bloom in a split second, sending an aggressive wave of glowing pink petals toward the camera",
    "a lightning storm over a neon-lit fantasy ocean, each bolt illuminating massive glowing waves below",

    # Ancient Relic Activation
    "a giant stone statue's eyes cracking open glowing with intense amber light as ancient runes illuminate across its mossy face",
    "an overgrown stone temple door slowly pushing open, warm golden light and floating petals pouring out from inside",

]

# MIRA = {
#     "name": "Mira",
#     "real_world": "an ordinary young woman — tired after a long day, sitting at a messy desk, "
#                   "walking through a grey city, or waiting for the bus. Deeply relatable.",
#     "crossing_moment": "something small and magical catches her eye — a door that wasn't there, "
#                        "a reflection that moves differently, a light under the floorboards. "
#                        "She pauses. Then steps through.",
#     "in_other_world": "her eyes widen. She touches surfaces with wonder. Emotionally present, not robotic.",
#     "visual_signature": "always in her ordinary real-world outfit — the contrast between "
#                         "ordinary clothes and extraordinary world is the visual hook.",
# }

def _call_gemini(prompt: str) -> dict:
    for attempt in range(3):
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
            print(f"Generation error (attempt {attempt+1}): {e}")
    return {}



# WORLDS = [
#     "a living ancient Egyptian city at golden hour",
#     "an underwater kingdom made of coral and bioluminescent light",
#     "a floating sky city above the clouds",
#     "a forest where every tree is made of stained glass",
#     "a cyberpunk Tokyo street market at midnight",
#     "a Viking longhouse during a feast",
#     "a library that contains every book ever written, infinite floors",
#     "a field of giant luminescent mushrooms at night",
#     "a Renaissance Italian city during a festival",
#     "a space station orbiting a ringed planet",
#     "an Aztec temple city at sunrise",
#     "a world where everything is made of paper and origami",
#     "a steampunk London with airships and brass gears",
#     "a frozen ice palace at the edge of the world",
#     "a world made entirely of light and color",
# ]

# BASELINE_NICHES = [
#     {"niche": "CAD/3D designers", "dream_world": "their blueprint becomes a living city they walk through"},
#     {"niche": "architecture students", "dream_world": "their sketch renders into a real building around them"},
#     {"niche": "marine biologists", "dream_world": "swimming through their research subjects at full scale"},
#     {"niche": "historians", "dream_world": "standing inside the moment they've studied their whole life"},
#     {"niche": "game designers", "dream_world": "entering the game world they've been building"},
#     {"niche": "textile artists", "dream_world": "walking through a landscape made of their fabric patterns"},
#     {"niche": "urban planners", "dream_world": "their city plan comes to life around them"},
#     {"niche": "astronomy enthusiasts", "dream_world": "floating in the nebula they've only seen in photos"},
# ]

def generate_pixar_dream_story(research_report: dict = None, memories: list=None)-> dict:
    print("Research keys:", list(research_report.keys()))
    print("viral_worlds count:", len(research_report.get("viral_worlds", [])))
    print("top_story_formats count:", len(research_report.get("top_story_formats", [])))
    if not research_report:
        raise ValueError("Research report required")

    
    viral_worlds = research_report.get("viral_worlds", [])
    story_formats = research_report.get("top_story_formats", []) 
    
    if not viral_worlds or not story_formats:
        raise ValueError("Missing research data")
    
    recent = get_recent_content(days=5)  # last 5 days

    recent_worlds = [item["world"] for item in recent if item["world"]]
    available_worlds = [w for w in viral_worlds if w.get("world_name") not in recent_worlds] or viral_worlds

    selected_format = None
    if story_formats:
        fmt_weights = []
        for f in story_formats:
            try:
                fmt_weights.append(float(f.get("completion_rate_signal", 5)))
            except (ValueError, TypeError):
                fmt_weights.append(5.0)
        selected_format = random.choices(story_formats, weights=fmt_weights, k=1)[0]
 
    format_context = ""
    if selected_format:
        format_context = f"""
STORY FORMAT (from trend research — use this narrative structure):
Format: {selected_format.get("format_name")}
Story structure: {selected_format.get("story_structure")}
What makes it transporting: {selected_format.get("transport_mechanism")}
Visual style: {selected_format.get("visual_style")}
"""

    # Weighted random selection
    world_weights = []
    for w in available_worlds:
        try:
            world_weights.append(float(w.get("virality_signal", 5)))
        except (ValueError, TypeError):
            world_weights.append(5.0)
    selected_world = random.choices(available_worlds, weights=world_weights, k=1)[0]

    hooks = research_report.get("top_emotional_hooks", [])
    emotion_context = hooks[0] if hooks else {"emotion": "awe and longing", "visual_execution": "wide establishing shot with warm light"}
 
    memory_context = ""
    if memories:
        memory_context = f"Past top performers to match tone and emotional depth:\n{json.dumps(memories[:2], indent=2)}"

    result = _call_gemini(f"""
You are an Academy Award-winning Pixar Animation Director and Story Artist creating a emotionally engaging animated short film.

Generate scenes that feel like a beautiful Disney/Pixar storybook brought to life.

Every shot should be EXTREMELY VISUAL and CINEMATIC.

Focus on:
- events that the ai can understand and generate visually (avoid abstract concepts and long words)
- do not use complex words, simple words and adjectives are enough

CHARACTER:
Feel free to create some irresistibly cute animated protagonist Disney/Pixar-level personality. The character should be something out of a movie and the scene should depict a key part of that movie, or a part that would get views
Add some vibrancy and color to the scenes and make the events clear
                          
Examples:
- Curious fox cub
- Tiny dragon
- Baby otter
- Shy forest spirit
- Young magical creature
- anything else etc.

SETTING/WORLD:
{selected_world.get('world_name')}

World Palette/Aesthetic:
{selected_world.get('color_palette')}

Lighting:
{selected_world.get('lighting')}

STORY CONTEXT:
Structure: {format_context}

Core Emotion:
{emotion_context.get('emotion')}

SHOT DESIGN RULES:
- Vertical 9:16 composition
- 20-25 seconds total

Return ONLY valid JSON:

{{
  "sora_prompt": "Write a cinematic story. Write the story to get the ai video generator to fully delve into the beauty and the enjoyableness of the scene. cinematic storytelling. Maximum 180 words.",
  
  "world_name": "{selected_world.get('world_name')}",
  
  "format_used": "{selected_format.get('format_name') if selected_format else 'cinematic animated short'}",
  
  "episode_title": "4-5 word Pixar-style title.",
  
  "main_story": "1-2 sentences summarizing the emotional story and magical climax.",
  
  "caption": "1-2 emotionally engaging sentences designed to maximize shares and audience attachment to the character.",
  
  "hashtags": ["#pixar", "#disneyanimation", "#aianimation", "#storytelling", "#animatedshort", "#3danimation", "#cinematic", "#cutecharacters", "#fantasyanimation", "#heartwarming"],
  
  "hook": "under 6 words — something that will catch the reader in 3 seconds",
  
  "duration_seconds": 25,
  
  "content_type": "pixar_cinematic_story"
}}

REFERENCE QUALITY:

Generate every beat with this same level of visual richness, character detail, emotional storytelling, and cinematic imagery.
""")

    if result:
        result["content_type"] = "pixar_dream_story"
        store_generated_content(result)
        print(f"Story: {result.get('episode_title')} | Format: {selected_format.get('format_name')}")
    
    return result

def generate_niche_story(research_report: dict=None, memories: list = None) -> dict:
    if not research_report :
        raise ValueError("Research report is required")

    recent = get_recent_content(days=5)
    recent_niches = [item.get("niche") for item in recent if item.get("niche")]

    niches = research_report.get("top_niches", []) or research_report.get("niche_communities", []) or research_report.get("raw", {}).get("niche_communities", [])
    if not niches:
        raise ValueError("No niches in research report, re-run scraper")
    
    available_niches = [n for n in niches if n.get("niche") not in recent_niches] or niches
 
    niche_weights = []
    for n in available_niches:
        try:
            niche_weights.append(float(n.get("shareability", 5)))
        except (ValueError, TypeError):
            niche_weights.append(5.0)
    niche = random.choices(available_niches, weights=niche_weights, k=1)[0]

    worlds = research_report.get("viral_worlds", [])
    world_context = ""
    if worlds:
        world_context = (f"Trending world for dream destination (use if it fits): "
                        f"{worlds[0].get('world_name')} — {worlds[0].get('visual_description')}")
    wizard_desc = get_character_description("Magic Hour Wizard")
    memory_context = ""
    if memories:
        memory_context = f"Past niche stories that performed:\n{json.dumps(memories[:2], indent=2)}"

    result = _call_gemini(f"""
You are creating a viral short-form video for a specific professional community. **Chloe vs. History style niche dream transformation stories** with the Magic Hour Wizard for Magic Hour text-to-video.

Avoid these recently used elements (do not repeat them):
Recent Niches: {recent_niches[:6]}

Character Consistency:
**Magic Hour Wizard (Silly Mascot):**
Wizard: {wizard_desc}
He appears as the magical catalyst — pops in, does something silly, then triggers the beautiful transformation.

NICHE (from current trend research):
Community: {niche.get('niche')}
Their real work scene: {niche.get('real_work_scene')}
Their dream transformation: {niche.get('dream_transformation')}
Insider detail only they'd recognize: {niche.get('insider_detail')}
Why they'd share it: {niche.get('share_trigger')}

CONCEPT: Start in their authentic real work environment.
Their work transforms — or they step/morph into the world — and it becomes their dream version.
People in this niche feel seen. Others feel awe and curiosity.

Ex NOT FOR COPY 1. A business owner struggles to create content, but with the meeting of Magic Hour Avatar(a fictional wizard representing the company) her life changes into bright colors and virality on the internet. The camera shots will be pleasantly displayed with her face sowing up in each magazine.
Ex 2.  A designer is struggling with a complex 3D model (mundane) and then it transforms into a beautiful, fully rendered world they can walk through (magical). The humor comes from the absurdity of the transformation but also the deep relatability of the struggle.
{world_context}

**Style Direction:**
- Mix of realistic/authentic opening + warm Pixar/Disney-style animation for the magical parts. This can be any 2D/3D style but unique.
- Keep the wizard consistent, cute, and not too salesy — more like a friendly magical friend.
- 9:16 vertical, 18-22 seconds.

RULES:
- Authentic real-world start (no stereotypes — use their specific insider detail)
- Transformation feels EARNED, not random — there's an emotional logic to it
- The dream version is visually specific and detailed, not vague
- Linger in the magical version — let it breathe
- NO ads

{memory_context}

Make the prompt less than 1000 characters!!
Return ONLY this JSON:
{{
  "sora_prompt": "Write the ACTUAL video prompt, not a description of what to write. Must follow this structure: 'Pixar/Disney 3D animation, 9:16 vertical. SCENE 1 (0-4s): [describe exactly what we see — the specific niche person, their specific tool/environment, their specific frustration using the insider detail]. SCENE 2 (4-8s): [the wizard pops in — describe his exact silly action and what goes wrong]. SCENE 3 (8-16s): [describe the magical transformation visually — colors, scale, movement, what the dream world looks like]. SCENE 4 (16-20s): [the niche person's reaction — close on their face, then wide shot of them in their dream world].' Be specific about: lighting, colors, camera movement, character expressions.",
  "niche": "{niche.get('niche')}",
  "episode_title": "short evocative title 4-6 words — specific to THIS niche (e.g. 'The Blueprint Comes Alive')",
  "real_world_scene": "specific authentic opening with insider detail",
  "wizard_entrance": "exactly what silly thing the wizard does",
  "transformation_moment": "exactly how the shift happens visually",
  "dream_world": "detailed magical version with colors and scale",
  "caption": "makes this niche feel seen, others feel awe",
  "hashtags": ["12-15 real hashtags — niche-specific + broad viral + AI/art"],
  "hook": "under 8 words — speaks directly to THIS niche",
  "duration_seconds": 20,
  "content_type": "niche_story"
}}
""")

    if result:
        result["content_type"] = "niche_story"
        store_generated_content(result)
        print(f"Niche story: {result.get('episode_title')} for {niche.get('niche')}")
    return result
    
def generate_flipped_meme(research_report: dict = None, memories: list = None) -> dict:
    recent = get_recent_content(days=5)
    recent_formats = [r.get("format") for r in recent if r.get("format")]
    recent_worlds = [r.get("world") for r in recent if r.get("world")]
 
    # Pick from proven formats, avoiding recent repeats
    available_formats = [f for f in PROVEN_VIRAL_FORMATS if f["name"] not in recent_formats] or PROVEN_VIRAL_FORMATS
    chosen_format = random.choice(available_formats)
 
    # Get trending world from research for the visual
    worlds = research_report.get("viral_worlds", []) if research_report else []
    world_context = ""
    if worlds:
        available_worlds = [w for w in worlds if w.get("world_name") not in recent_worlds] or worlds
        top_world = random.choice(available_worlds[:3])
        world_context = (
            f"Use this trending world for the magical/beautiful visual:\n"
            f"Name: {top_world.get('world_name')}\n"
            f"Visuals: {top_world.get('visual_description')}\n"
            f"Colors: {top_world.get('color_palette')}\n"
            f"Lighting: {top_world.get('lighting')}"
        )
 
    mira_desc = get_character_description("Mira")
    memory_context = ""
    if memories:
        memory_context = f"Past memes that performed well — match this energy:\n{json.dumps(memories[:2], indent=2)}"
 
    result = _call_gemini(f"""
    You generate VIRAL short-form meme video prompts.

    GOAL:
    Create a 9:16 AI video prompt that is:

    instantly relatable (0–2s)
    sudden chaotic or aesthetic switch (3–5s)
    strong meme payoff (6–9s)
    fast, loopable, high replay value

    INPUT FORMAT:
    Name: {chosen_format['name']}
    Structure: {chosen_format['structure']}
    Example: {chosen_format['example']}

    WORLD:
    {world_context}

    CHARACTER:
    {mira_desc or "expressive, adorable character or animal, exaggerated reactions"}

    {memory_context}

    STYLE RULES (STRICT):

    no filler words
    short, punchy phrases
    highly visual actions (no abstract narration)
    exaggerate reactions (gen z / brainrot energy allowed)
    prioritize RELATABLE → CHAOS → PAYOFF
    keep scenes simple but high contrast

    Keep the prompts concise — under 1000 characters. Focus on the specific visual details that will make the meme hit hard. The text overlay should be the star, with the visuals perfectly complementing it to maximize comedic impact and relatability.

    TEXT OVERLAY STYLE:

    lowercase
    3–6 words per line
    2–4 lines max
    last line = punchline

    GOOD EXAMPLE OUTPUT STYLE:

    relatable:
    "opening laptop"
    "seeing 6 assignments"

    cut →

    "my last braincell"
    (cat screaming in space)

    talking animal:
    "i'll start in 5 mins"
    "i swear"

    cut →

    dog: "we both know that's a lie"
    PRIORITY RULES (HIGHEST PRIORITY):

1. TEXT OVERLAYS DRIVE THE MEME.
   - Must be instantly relatable
   - Must clearly show the joke
   - Visuals only SUPPORT the text

2. KEEP VISUALS SIMPLE.
   - Avoid complex fantasy descriptions
   - Focus on character expressions and contrast
   - One clear action per scene

3. RELATABILITY > AESTHETIC.
   - Use everyday situations (school, procrastination, social moments)
   - If it’s not “this is literally me”, reject it

4. COMEDY = CONTRAST.
   - chaotic vs blank
   - effort vs failure
   - expectation vs reality

    Return ONLY JSON:

    {{
    "sora_prompt": "vertical 9:16. fast cuts. 0-2s, 2-4s: slight pause or zoom. 4s: hard cut or whip pan. 4-9s: use simple details like a story to match the text perfectly. short and concise",

    "text_overlays": [
    "0:00 first line",
    "0:02 second line",
    "0:04 punchline"
    ],

    "hook": "under 6 words, but funny and relatable",

    "meme_description": "specific relatable situation + twist",

    "comedy_payoff": "exact joke or irony",

    "aesthetic_payoff": "what makes visuals hit",

    "caption": "under 8 words, high shareability",

    "hashtags": ["#fyp","#relatable","#pov","#meme","#viral","#brainrot"],

    "duration_seconds": 9,
    "content_type": "flipped_meme"
    }}
    """)
 
    if result:
        result["content_type"] = "flipped_meme"
        result["format_used"] = chosen_format["name"]
        store_generated_content(result)
        print(f"Meme: {chosen_format['name']} — {result.get('meme_description', '')[:60]}")
    return result

def generate_awe_clip(research_report: dict = None) -> dict:

    import random

    if not research_report :
        raise ValueError("Research report is required")

    recent = get_recent_content(days=5)
    recent_niches = [item.get("niche") for item in recent if item.get("niche")]

    niches = research_report.get("top_niches", []) or research_report.get("niche_communities", []) or research_report.get("raw", {}).get("niche_communities", [])
    if not niches:
        raise ValueError("No niches in research report, re-run scraper")

    worlds = research_report.get("viral_worlds", [])

    result = _call_gemini(f"""
                          
Avoid these recently used elements (do not repeat them):
Recent Niches: {recent_niches[:6]}

You are a senior Pixar concept artist, Disney visual development painter, and fantasy children's book illustrator.

GOAL:

Create an image that makes someone stop scrolling because it feels beautiful, peaceful, and real.

The scene should feel like a photograph from a magical version of our world.

The magic should be subtle.

The environment is always the hero.

The viewer should first notice beauty and the vibrant colors. Make the colors match and maybe even add pastels.

WRITING STYLE:

Describe the image exactly like a photographer describing a shot.

Use simple concrete language.

Avoid poetic prose.

Avoid invented object names.

Avoid words like:
"ancient"
"mystical"
"legendary"
"enchanted"
"ethereal"
"otherworldly"
"arcane"

Make a beautiful scene. The scene should capture perfect moments and seem like an ilustration style. Create the moment that people would take pictures of and keep with them forever.
Add vibrant colors and something that is a makes the scene feel surreal. The colors should be cohesive like looking at an autumn scenery or looking at a faraway magical town.
 
The scene should give a happy an warm feeling. Colors are important!!
Add fiction and magic and even cute magical animals (if it fits with the background) or something from a fictional story. The illustrative background is the most important, the characters just fit within

Perfect Example: Leo's Celebration
"Leo, a small dirty blonde boy, stands on a raised platform in the center of the town, holding his glowing device with pride. Behind him, the townspeople cheer and clap under the luminous glow of the new lights, while the sky transitions into a warm purple dusk."

Return ONLY valid JSON:
{{
    "sora_prompt": "Write this in teh prompt for the ai 'Follow the given provided example images.' Describe exactly what is visible, the ai image generator can only understand the physical appearance.  Be clear. Add clear adjectives and create a beatiful visual story. 50 words.",
    "motion_prompt": "4-second seamless loop. Describe only gentle motion. Floating lanterns drift slowly, flower petals swirl softly, glowing creatures glide past, window lights flicker gently, water sparkles, fabric waves lightly. Under 50 words.",
    "visual_concept": "one sentence describing the magical moment",
    "caption": "under 8 words. dreamy, poetic, scroll-stopping",
    "hashtags": ["#aiart","#fantasyart","#pixarstyle","#storybook","#magicalworld","#dreamscape","#aestheticvideo","#cinematic","#fantasyillustration","#fyp","#viral","#loopvideo"],
    "hook": "under 5 words — pure wonder", 
    "duration_seconds": 4, 
    "content_type": "awe_clip"
}}
""")


    if result:
        result["content_type"] = "awe_clip"
        store_generated_content(result)
        print(f"Awe clip: {result.get('visual_concept', '')[:60]}")
    return result

def custom_video():
    pass

def daily_batch(research_report: dict) -> list[dict]:
    story_memories = get_best_performing_content(
        niche="general", content_type="pixar_dream_story", platform="tiktok", top_k=3
    )
    meme_memories = get_best_performing_content(
        niche="general", content_type="flipped_meme", platform="tiktok", top_k=3
    )
    niche_memories = get_best_performing_content(
        niche="general", content_type="niche_story", platform="tiktok", top_k=3
    )

    batch = [
        {**generate_pixar_dream_story(research_report, story_memories), "scheduled_time": "09:00"},
        {**generate_flipped_meme(research_report, meme_memories),"scheduled_time": "13:00"},
        {**generate_niche_story(research_report, niche_memories),"scheduled_time": "19:00"},
    ]

    print(f"\nDaily batch ready:")
    for item in batch:
        title = item.get("episode_title") or item.get("meme_description") or item.get("niche", "")
        print(f" {item['scheduled_time']} — {item['content_type']}: {title}")
 
    return batch

if __name__ == "__main__":
    from scraper import run_research
    print("Running research...")
    report = run_research()
 
    print("\nGenerating daily batch...\n")
    batch = daily_batch(report)
 
    for item in batch:
        print(f"\n{'='*50}")
        print(f"Type: {item['content_type']} | Time: {item['scheduled_time']}")
        print(f"Hook: {item.get('hook')}")
        print(f"Caption: {item.get('caption', '')[:100]}")
        print(f"Prompt: {item.get('sora_prompt', '')[:120]}...")

