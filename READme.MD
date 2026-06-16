# Magic Hour Agent 🎬

Automated short-form video pipeline: **research → prompt → AI video → post → analyze → improve**.  
Set your niche once. It runs itself.

---

## How it works

```
prompt_engineer.py        ← describe your content once, Gemini writes your creative brief
       ↓
scraper.py                ← researches trends specific to your niche
       ↓
user_prompt_generator.py  ← your brief + trend data → video prompt
       ↓
magichour.py              ← turns the prompt into a video
       ↓
main.py                   ← posts on your schedule via Postiz
       ↓
analyzer.py               ← OpenClaw pulls performance data, rewrites your brief
```

---

## Setup (do this once)

### 1. Clone and install

```bash
git clone https://github.com/samriddhighosh/magic-hour-agent
cd magic-hour-agent
pip install -r requirements.txt
```

### 2. Add your API keys

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=AIza...
MAGICHOUR_API_KEY=mh_...
PINECONE_API_KEY=pc-...

# Postiz — your ngrok URL, no trailing slash
POSTIZ_URL=https://xxxx-xx-xx-xxx-xx.ngrok-free.app
POSTIZ_API_KEY=your_postiz_api_key

# Per-platform integration IDs (from Postiz → Integrations)
POSTIZ_CHANNEL_TIKTOK=your_integration_id
POSTIZ_CHANNEL_INSTAGRAM=your_integration_id
POSTIZ_CHANNEL_YOUTUBE=your_integration_id

# Discord (optional — for notifications)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# OpenClaw (for post analysis and auto-improvement)
OPENCLAW_API_KEY=your_openclaw_key
```

---

### 3. Install and run Postiz on ngrok

Postiz is the scheduler that handles actual posting to TikTok, Instagram, YouTube, and X.

#### Install Postiz

```bash
git clone https://github.com/gitroomhq/postiz-app
cd postiz-app
cp .env.example .env
```

Edit `.env` inside postiz-app — the minimum you need:

```env
DATABASE_URL="postgresql://postgres:password@localhost:5432/postiz"
REDIS_URL="redis://localhost:6379"
JWT_SECRET="any-long-random-string"
BACKEND_INTERNAL_URL="http://localhost:3000"
NEXT_PUBLIC_BACKEND_URL="http://localhost:3000"
FRONTEND_URL="http://localhost:4200"
```

Start it:

```bash
docker-compose up -d
```

Postiz runs on `http://localhost:3000` (API) and `http://localhost:4200` (UI).

#### Expose with ngrok

```bash
# Install ngrok if you haven't: https://ngrok.com/download
ngrok http 3000
```

Copy the HTTPS URL ngrok gives you (e.g. `https://abc123.ngrok-free.app`) and put it in your `.env`:

```env
POSTIZ_URL=https://abc123.ngrok-free.app
```

> **Every time ngrok restarts it gives you a new URL.** Update `POSTIZ_URL` in `.env` when that happens, or use a paid ngrok account with a fixed domain.

#### Get your Postiz API key

1. Open `http://localhost:4200` in your browser
2. Create an account and log in
3. Go to **Settings → API Key** → copy it → paste into `POSTIZ_API_KEY` in `.env`

#### Connect your social accounts

1. Go to **Integrations** in the Postiz UI
2. Connect each platform (TikTok, Instagram, YouTube, X)
3. Each platform will ask for its own credentials:

| Platform  | What you need                                                               |
| --------- | --------------------------------------------------------------------------- |
| TikTok    | TikTok developer app — client key + secret (apply at developers.tiktok.com) |
| Instagram | Meta Business account + Facebook app (developers.facebook.com)              |
| YouTube   | Google Cloud project + OAuth 2.0 credentials (console.cloud.google.com)     |
| X         | X developer app API keys (developer.twitter.com)                            |

4. After connecting, click the integration to find its **Integration ID**
5. Add each ID to your `.env`:

```env
POSTIZ_CHANNEL_TIKTOK=abc123
POSTIZ_CHANNEL_INSTAGRAM=def456
```

---

### 4. Install OpenClaw

OpenClaw is the agent that analyzes your post performance and automatically improves your creative brief.

#### Install

```bash
pip install openclaw
```

Or if you're running it as a local agent server (from the screenshot — `.agents/skills/postiz`):

```bash
cd ~/.agents
npm install   # or yarn, depending on your setup
npm run start
```

#### Configure OpenClaw to watch this project

In your OpenClaw agent config (usually `~/.agents/config.json` or via the OpenClaw dashboard), add this project as a monitored workflow:

```json
{
  "workflows": [
    {
      "name": "magic-hour-agent",
      "project_path": "/path/to/magic-hour-agent",
      "analysis_file": "analyzer.py",
      "brief_file": "user_system_prompt.txt",
      "trigger": "after_post"
    }
  ]
}
```

OpenClaw will call `analyzer.py` after each post and rewrite `user_system_prompt.txt` when it finds patterns worth acting on.

---

### 5. Describe your content

```bash
python prompt_engineer.py
```

Answer three questions — what kind of videos, visual style, what to avoid. Gemini writes your creative brief to `user_system_prompt.txt`.

To update your style later: `python prompt_engineer.py --load`

---

### 6. Run

```bash
# Make sure everything works before posting anything
python main.py --test

# Generate one video and post it right now
python main.py --now

# Start the daily scheduler
python main.py
```

---

## Post analysis and auto-improvement

`analyzer.py` runs after every post. It does three things:

1. **Pulls metrics** from Postiz for the last 7 days of posts
2. **Sends them to OpenClaw** which identifies what's working (hooks, visual styles, caption patterns) and what isn't
3. **Rewrites `user_system_prompt.txt`** to double down on what performs and drop what doesn't

You can also trigger it manually:

```bash
# Analyze last 7 days and update your brief
python analyzer.py

# Analyze without updating the brief (just see the report)
python analyzer.py --report-only

# Force a full rewrite of your brief from scratch based on performance
python analyzer.py --rewrite
```

The analysis report is saved to `analysis_report.json` each run so you can read it yourself.

---

## Running multiple channels

Give each channel its own config and brief:

```
magic-hour-agent/
├── configs/
│   ├── fantasy.yaml
│   ├── fitness.yaml
│   └── finance_memes.yaml
├── briefs/
│   ├── fantasy_brief.txt
│   ├── fitness_brief.txt
│   └── finance_brief.txt
```

```bash
python main.py --config configs/fantasy.yaml
python main.py --config configs/fitness.yaml
```

Point each config to its own brief file and Postiz integration IDs.

---

## Troubleshooting

| Problem                            | Fix                                                                    |
| ---------------------------------- | ---------------------------------------------------------------------- |
| `GEMINI_API_KEY missing`           | Add to `.env`                                                          |
| `user_system_prompt.txt not found` | Run `python prompt_engineer.py`                                        |
| `Postiz 401`                       | Copy API key from Postiz → Settings → API Key                          |
| Postiz connection refused          | Make sure `docker-compose up -d` is running in the postiz-app folder   |
| ngrok URL changed                  | Update `POSTIZ_URL` in `.env` with the new ngrok URL                   |
| `No niches in research`            | Run `python scraper.py` directly to debug                              |
| Video file too small               | Magic Hour generation failed — check `MAGICHOUR_API_KEY`               |
| TikTok posts fail                  | TikTok needs a developer app — see developers.tiktok.com               |
| OpenClaw not improving brief       | Check `analysis_report.json` — needs at least 5 posts to find patterns |

---

## Files

```
magic-hour-agent/
├── prompt_engineer.py        ← run this first to set your content style
├── user_system_prompt.txt    ← your creative brief (auto-created, auto-improved)
├── user_prompt_generator.py  ← uses your brief to build video prompts
├── analyzer.py               ← OpenClaw performance analysis + brief improvement
├── scraper.py                ← trend research tuned to your niche
├── magichour.py              ← Magic Hour API integration
├── main.py                   ← scheduler + posting
├── channel_config.yaml       ← schedule, platforms, channel name
├── pinecone_store.py         ← performance memory
├── analysis_report.json      ← latest analysis output (auto-created)
└── .env                      ← all secrets (never commit this)
```
