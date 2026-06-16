
import os
from pathlib import Path
from dotenv import load_dotenv
 
load_dotenv()
 
try:
    import yaml
    _yaml_available = True
except ImportError:
    _yaml_available = False
 
 
def _load_yaml(path: str = "channel_config.yaml") -> dict:
    if not _yaml_available:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with open(p) as f:
        return yaml.safe_load(f) or {}
 
 
def _env_or_yaml(env_key: str, yaml_value: str) -> str:
    """Prefer .env, fall back to yaml value."""
    return os.getenv(env_key, yaml_value or "")
 
 
class ChannelConfig:
    def __init__(self, yaml_path: str = "channel_config.yaml"):
        raw = _load_yaml(yaml_path)
 
        ch = raw.get("channel", {})
        creds = raw.get("credentials", {})
        adv = raw.get("advanced", {})
 
        # ── Channel identity ──────────────────────────────────────────────
        self.channel_name: str = ch.get("name", "My Channel")
        self.niche: str = ch.get("niche", "general")
        self.content_types: list[str] = ch.get("content_types", ["awe_clip", "pixar_dream_story"])
        self.example_videos: list[str] = [v for v in ch.get("example_videos", []) if v]
        self.style_notes: str = ch.get("style_notes", "")
        self.target_audience: str = ch.get("target_audience", "general audience")
        self.avoid: str = ch.get("avoid", "")
 
        # ── Schedule & platforms ──────────────────────────────────────────
        self.schedule: list[dict] = raw.get("schedule", [
            {"time": "09:00", "type": "awe_clip"},
            {"time": "15:00", "type": "pixar_dream_story"},
            {"time": "20:00", "type": "awe_clip"},
        ])
        self.platforms: list[str] = raw.get("platforms", ["tiktok", "instagram", "youtube"])
 
        # ── API credentials (prefer .env over yaml) ───────────────────────
        self.gemini_key: str = _env_or_yaml("GEMINI_API_KEY", creds.get("gemini_api_key", ""))
        self.magichour_key: str = _env_or_yaml("MAGICHOUR_API_KEY", creds.get("magichour_api_key", ""))
        self.pinecone_key: str = _env_or_yaml("PINECONE_API_KEY", creds.get("pinecone_api_key", ""))
        self.pinecone_index: str = _env_or_yaml("PINECONE_INDEX", creds.get("pinecone_index", "magichour-memory"))
 
        self.postiz_url: str = _env_or_yaml("POSTIZ_URL", creds.get("postiz_url", ""))
        self.postiz_api_key: str = _env_or_yaml("POSTIZ_API_KEY", creds.get("postiz_api_key", ""))
        self.discord_webhook: str = _env_or_yaml("DISCORD_WEBHOOK_URL", creds.get("discord_webhook_url", ""))
 
        # Per-platform Postiz integration IDs
        yaml_channels: dict = creds.get("postiz_channels", {})
        self.postiz_channels: dict[str, str] = {}
        for p in ["tiktok", "instagram", "youtube", "x"]:
            env_val = os.getenv(f"POSTIZ_CHANNEL_{p.upper()}", "")
            yaml_val = yaml_channels.get(p, "")
            val = env_val or yaml_val
            if val:
                self.postiz_channels[p] = val
 
        # ── Advanced ──────────────────────────────────────────────────────
        self.research_cache_hours: int = adv.get("research_cache_hours", 12)
        self.batch_size: int = adv.get("batch_size", 3)
        self.test_mode: bool = (
            os.getenv("TEST_MODE", "").lower() == "true"
            or adv.get("test_mode", False)
        )
 
    def style_block(self) -> str:
        """Returns a formatted string to inject into LLM prompts."""
        parts = []
        if self.niche:
            parts.append(f"Channel niche: {self.niche}")
        if self.target_audience:
            parts.append(f"Target audience: {self.target_audience}")
        if self.style_notes:
            parts.append(f"Visual / tone style:\n{self.style_notes}")
        if self.avoid:
            parts.append(f"Avoid these themes: {self.avoid}")
        if self.example_videos:
            parts.append("Reference videos to match vibe:\n" + "\n".join(f"  - {v}" for v in self.example_videos))
        return "\n\n".join(parts)
 
    def validate(self) -> list[str]:
        """Returns a list of warning strings for missing critical config."""
        warnings = []
        if not self.gemini_key:
            warnings.append("GEMINI_API_KEY is missing — LLM generation will fail")
        if not self.magichour_key:
            warnings.append("MAGICHOUR_API_KEY is missing — video generation will fail")
        if not self.postiz_url or not self.postiz_api_key:
            warnings.append("Postiz credentials missing — auto-posting will be skipped")
        if not self.postiz_channels:
            warnings.append("No Postiz integration IDs set — auto-posting will be skipped")
        return warnings
 
    def __repr__(self):
        return (
            f"<ChannelConfig niche={self.niche!r} "
            f"platforms={self.platforms} "
            f"content_types={self.content_types} "
            f"test_mode={self.test_mode}>"
        )
 
 
# Singleton — import this everywhere
cfg = ChannelConfig()