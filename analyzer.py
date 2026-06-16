"""
analyzer.py — post performance analysis and automatic brief improvement.

Pulls metrics from Postiz, sends them to OpenClaw for pattern analysis,
and rewrites user_system_prompt.txt to improve future content.

Usage:
    python analyzer.py                # analyze + update brief if patterns found
    python analyzer.py --report-only  # analyze only, don't touch the brief
    python analyzer.py --rewrite      # force full rewrite of the brief
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from google import genai

load_dotenv()

BRIEF_FILE = "user_system_prompt.txt"
REPORT_FILE = "analysis_report.json"
DESCRIPTION_FILE = "channel_description.json"

postiz_url = os.getenv("POSTIZ_URL", "").rstrip("/")
postiz_api_key = os.getenv("POSTIZ_API_KEY", "")
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))


# ── Pull post metrics from Postiz ────────

def fetch_recent_posts(days: int = 7) -> list[dict]:
    """Fetches posts from the last N days via Postiz API."""
    if not postiz_url or not postiz_api_key:
        print("Postiz credentials missing — skipping metric fetch.")
        return []

    headers = {
        "Authorization": postiz_api_key,
        "ngrok-skip-browser-warning": "true",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.get(
            f"{postiz_url}/api/public/v1/posts",
            headers=headers,
            params={"limit": 50},
            timeout=15,
        )
        resp.raise_for_status()
        all_posts = resp.json()

        # Filter to last N days
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = []
        for post in (all_posts if isinstance(all_posts, list) else all_posts.get("posts", [])):
            posted_at_str = post.get("publishDate") or post.get("createdAt", "")
            try:
                posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                if posted_at >= cutoff:
                    recent.append(post)
            except Exception:
                recent.append(post)  # include if date can't be parsed

        print(f"Fetched {len(recent)} posts from the last {days} days.")
        return recent

    except requests.exceptions.ConnectionError:
        print("Could not connect to Postiz. Is ngrok running? Is docker-compose up?")
        return []
    except Exception as e:
        print(f"Postiz fetch error: {e}")
        return []


def extract_metrics(posts: list[dict]) -> list[dict]:
    metrics = []
    for post in posts:
        # Postiz stores platform-specific analytics nested under each post
        analytics = post.get("analytics") or {}
        caption = ""
        for p in post.get("posts", []):
            for v in p.get("value", []):
                if v.get("content"):
                    caption = v["content"]
                    break

        metrics.append({
            "id": post.get("id"),
            "caption": caption[:200],
            "platform": post.get("integration", {}).get("providerIdentifier", "unknown"),
            "posted_at": post.get("publishDate") or post.get("createdAt"),
            "views": analytics.get("views") or analytics.get("impressions") or 0,
            "likes": analytics.get("likes") or analytics.get("reactions") or 0,
            "shares": analytics.get("shares") or analytics.get("reposts") or 0,
            "comments": analytics.get("comments") or 0,
            "follows": analytics.get("follows") or analytics.get("newFollowers") or 0,
        })
    return metrics


# ── Load stored prompt metadata from pinecone/local ─────

def load_stored_prompts() -> list[dict]:
    """Loads prompt packages that were stored at post time (from pinecone_store)."""
    try:
        from pinecone_store import get_recent_content
        return get_recent_content(days=7)
    except Exception:
        return []


# ── OpenClaw analysis ──────────

def analyze_with_openclaw(metrics: list[dict], prompts: list[dict]) -> dict:

    openclaw_key = os.getenv("OPENCLAW_API_KEY", "")

    if openclaw_key:
        return _openclaw_api_analysis(metrics, prompts, openclaw_key)
    else:
        print("OPENCLAW_API_KEY not set — using Gemini for analysis.")
        return _gemini_analysis(metrics, prompts)


def _openclaw_api_analysis(metrics: list[dict], prompts: list[dict], api_key: str) -> dict:
    """Calls the OpenClaw agent API for analysis."""
    try:
        resp = requests.post(
            "https://api.openclaw.ai/v1/analyze",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "posts": metrics,
                "prompts": prompts,
                "task": "identify_performance_patterns",
                "context": "short_form_video_social_media",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"OpenClaw API error: {e} — falling back to Gemini analysis.")
        return _gemini_analysis(metrics, prompts)


def _gemini_analysis(metrics: list[dict], prompts: list[dict]) -> dict:
    """Uses Gemini to analyze performance patterns when OpenClaw is unavailable."""
    if not metrics:
        return {"patterns": [], "recommendations": [], "confidence": "low"}

    sorted_metrics = sorted(metrics, key=lambda x: x.get("views", 0), reverse=True)
    top = sorted_metrics[:5]
    bottom = sorted_metrics[-5:] if len(sorted_metrics) > 5 else []

    prompt = f"""
You are a social media performance analyst specializing in short-form video.

Analyze this post performance data and identify clear patterns.

TOP PERFORMING POSTS (highest views):
{json.dumps(top, indent=2)}

LOWEST PERFORMING POSTS:
{json.dumps(bottom, indent=2)}

ALL PROMPT DATA USED:
{json.dumps(prompts[:10], indent=2)}

Identify:
1. What visual styles, hooks, or caption patterns appear in top performers
2. What appears in low performers that should be avoided
3. Specific changes to make to the creative brief to improve performance
4. Confidence level in these findings (low/medium/high — needs 5+ posts for high)

Return ONLY valid JSON:
{{
    "top_performers": ["pattern 1", "pattern 2"],
    "low_performers": ["pattern 1", "pattern 2"],
    "recommendations": [
        "specific actionable change 1",
        "specific actionable change 2"
    ],
    "brief_additions": "text to ADD to the creative brief based on what's working",
    "brief_removals": "text describing what to REMOVE or soften in the brief",
    "confidence": "low/medium/high",
    "posts_analyzed": {len(metrics)},
    "summary": "2-3 sentence plain English summary of findings"
}}
"""
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rstrip("`").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini analysis error: {e}")
        return {"patterns": [], "recommendations": [], "confidence": "low"}


# ── Brief rewriter ─────────────

def rewrite_brief(analysis: dict, force: bool = False) -> bool:

    confidence = analysis.get("confidence", "low")
    posts_analyzed = analysis.get("posts_analyzed", 0)

    if not force:
        if confidence == "low" or posts_analyzed < 5:
            print(f"Not enough data to rewrite brief (confidence: {confidence}, posts: {posts_analyzed}).")
            print("Keep posting — the brief will auto-improve once more data is available.")
            return False

    if not os.path.exists(BRIEF_FILE):
        print(f"{BRIEF_FILE} not found — run `python prompt_engineer.py` first.")
        return False

    with open(BRIEF_FILE, "r") as f:
        current_brief = f.read()

    rewrite_prompt = f"""
You are rewriting a creative brief for a short-form video channel based on real performance data.

CURRENT BRIEF:
{current_brief}

PERFORMANCE ANALYSIS:
What's working (keep and amplify): {analysis.get('brief_additions', '')}
What's not working (reduce or remove): {analysis.get('brief_removals', '')}
Specific recommendations: {json.dumps(analysis.get('recommendations', []))}

Rewrite the creative brief to incorporate these findings. Keep the same structure and length.
Amplify what's working. Soften or remove what isn't. Don't change the core identity.

Write ONLY the updated brief text. No headers, no markdown, no explanation.
"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash", contents=rewrite_prompt
        )
        new_brief = response.text.strip()

        # Back up the current brief before overwriting
        backup_path = f"{BRIEF_FILE}.backup_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
        with open(backup_path, "w") as f:
            f.write(current_brief)

        # Write the improved brief
        header = (
            f"# user_system_prompt.txt\n"
            f"# Auto-improved by analyzer.py on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"# Based on {posts_analyzed} posts — confidence: {confidence}\n"
            f"# Previous version backed up to: {backup_path}\n\n"
        )
        with open(BRIEF_FILE, "w") as f:
            f.write(header + new_brief)

        print(f"\nBrief updated. Previous version saved to {backup_path}")
        return True

    except Exception as e:
        print(f"Brief rewrite error: {e}")
        return False


# ── Save report ──────────

def save_report(analysis: dict, metrics: list[dict]):
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "posts_analyzed": len(metrics),
        "analysis": analysis,
        "raw_metrics": metrics,
    }
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {REPORT_FILE}")


# ── Main ─────────

def run(report_only: bool = False, force_rewrite: bool = False):
    print(f"\nAnalyzing post performance...")

    posts = fetch_recent_posts(days=7)
    metrics = extract_metrics(posts)
    stored_prompts = load_stored_prompts()

    if not metrics:
        print("No posts found. Post some content first, then run analyzer.py.")
        return

    print(f"Analyzing {len(metrics)} posts...")
    analysis = analyze_with_openclaw(metrics, stored_prompts)

    save_report(analysis, metrics)

    print(f"\n── Analysis summary ────────")
    print(analysis.get("summary", "No summary available."))
    print(f"\nConfidence: {analysis.get('confidence', 'unknown')}")
    print(f"Posts analyzed: {analysis.get('posts_analyzed', len(metrics))}")

    if analysis.get("recommendations"):
        print("\nRecommendations:")
        for r in analysis["recommendations"]:
            print(f"  - {r}")

    if not report_only:
        print("\nUpdating creative brief...")
        updated = rewrite_brief(analysis, force=force_rewrite)
        if updated:
            print("Brief improved. Next generated video will use the updated brief.")
    else:
        print("\n(--report-only mode: brief not updated)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze post performance and improve creative brief")
    parser.add_argument("--report-only", action="store_true", help="Analyze but don't update the brief")
    parser.add_argument("--rewrite", action="store_true", help="Force full brief rewrite regardless of confidence")
    args = parser.parse_args()

    run(report_only=args.report_only, force_rewrite=args.rewrite)