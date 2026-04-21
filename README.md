# Veritas - AI Fact-Checker for Short-Form Video

**Every day, millions of people scroll through TikTok, Instagram Reels, and YouTube Shorts. Some of those videos contain misinformation that spreads faster than anyone can debunk it. I built Veritas to try and change that.**

Paste a video link. In under 2 minutes, Veritas downloads the video, transcribes what's being said, reads what's shown on screen, searches the web for real sources, checks for recycled footage, runs a deepfake scan, and gives you a verdict with per-claim citations so you can see *exactly* why something is true, false, or somewhere in between.

This is a solo student project built as a portfolio piece and scholarship submission. It's fully functional, publicly deployed, and free to try.

---

## Try It Live

**Web app:** [project-veritas-mauve.vercel.app](https://project-veritas-mauve.vercel.app)

**Android APK:** [Download from Google Drive](https://drive.google.com/drive/folders/1rVRPF7ERl7owPsx7zZM2pEgYqnotcIvN?usp=sharing)

*The backend runs on Render's free tier, so the first scan may take an extra 30-60 seconds while the server wakes up. After that, scans usually finish in 1-2 minutes.*

---

## What It Does

When you submit a video URL, Veritas runs a multi-stage analysis pipeline:

1. **Subtitle extraction** - Checks for existing captions first (instant) before falling back to audio transcription.
2. **Video download & frame extraction** - Downloads the video via yt-dlp and pulls representative frames for visual analysis.
3. **Speech-to-text** - Converts spoken audio to text using Google Speech Recognition, capped at 120 seconds for speed.
4. **Visual + deepfake analysis** - A single Claude AI vision call reads all on-screen text (captions, overlays, headlines, graphs) and checks for deepfake/AI-generation indicators at the same time.
5. **Reverse image search** - Uploads a key frame to Google Lens via SerpApi to detect if footage has been recycled or taken out of context from older content.
6. **Web search** - Queries DuckDuckGo, Wikipedia, Brave Search, and Tavily in parallel to find real sources related to the claims.
7. **AI fact-check** - Claude Sonnet looks at the transcript + visual content + web sources and produces a structured verdict with per-claim explanations and citations.

All of these steps run in parallel where possible. Source citations are gated, meaning the AI can only cite URLs that came back from real web searches. Fabricated citations are automatically detected, dropped, and logged.

---

## Why I Built This

I'm a student who noticed that fact-checking is almost always focused on text articles and tweets. Short-form video, the format that actually dominates how young people get their news, gets almost no automated fact-checking coverage.

Existing tools either require manual effort (journalists writing debunks days later) or only handle text. Nothing I could find takes a TikTok link and gives you a sourced verdict in minutes.

Veritas is my attempt to fill that gap. It's not perfect (no AI fact-checker is), but it shows that the pipeline is technically feasible and practically useful, even on completely free infrastructure.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, MongoDB Atlas (free M0) |
| **AI** | Claude Sonnet 4.6 (fact-checking, visual analysis), Claude Haiku 4.5 (search query extraction) |
| **Video processing** | yt-dlp, ffmpeg, Google Speech Recognition (free) |
| **Web search** | Tavily, DuckDuckGo, Wikipedia API, Brave Search |
| **Reverse image** | imgbb + SerpApi Google Lens |
| **Web frontend** | React + TypeScript + Vite, deployed on Vercel |
| **Mobile app** | React Native + Expo, EAS Build for Android APK |
| **Hosting** | Render (backend, free tier), Vercel (web, free tier), MongoDB Atlas (free M0) |

Total monthly cost: **$0**. The entire stack runs on free tiers.

---

## Architecture

```
User (Web or Mobile App)
   |
   |  POST /api/fact-check     ->  202 { job_id }
   |  GET  /api/fact-check/{id}/status  (poll every 2s)
   |
   v
FastAPI Backend (Render)
   |
   +-- Subtitles check (fast, no download needed)
   |
   +-- Video download (yt-dlp, 2 strategies, 60s timeout)
   |
   +-- +-- Visual + Deepfake analysis --- Claude Sonnet (1 combined call)
   |   +-- Audio transcription --------- Google STT (120s cap, 2 chunks)
   |   +-- Reverse image search -------- imgbb -> SerpApi Google Lens
   |   +-- Web search (if subtitles found early, runs in parallel)
   |
   +-- Web context search -- Tavily + DDG + Wikipedia + Brave (parallel)
   |
   +-- Final fact-check ---- Claude Sonnet (verdict + per-claim citations)
       |
       +-- Citation gating: only real search URLs allowed, fabricated ones dropped
   
MongoDB Atlas
   +-- users          (auth, bcrypt-hashed passwords)
   +-- fact_check_jobs (TTL-indexed, auto-deletes after 1h)
   +-- scans          (scan history per user)
```

Key design decisions:
- **Subtitles first** - Checking for existing captions before downloading saves 30-60 seconds on videos that already have them.
- **Parallel execution** - Deepfake, visual analysis, transcription, and reverse image search all run at the same time.
- **Citation gating** - The AI gets a numbered source pool from real web searches and can only cite those IDs. Any hallucinated URL gets automatically dropped.
- **Capped transcription** - Audio is capped at 120 seconds (2 chunks max) to balance transcript completeness with speed on free infrastructure.

---

## Project Structure

```
Project Veritas/
+-- backend/
|   +-- server.py              FastAPI entry point
|   +-- config.py              Environment vars, plan config, paths
|   +-- database.py            Motor async MongoDB client
|   +-- models.py              Pydantic models (claims, verdicts, deepfake results)
|   +-- jobs.py                MongoDB-backed async job queue
|   +-- routes/                HTTP route handlers
|   |   +-- fact_check.py        Scan submission + polling
|   |   +-- auth.py              Login, register, JWT
|   |   +-- subscription.py      Plan limits + scan logging
|   |   +-- ...
|   +-- services/              Core business logic
|   |   +-- video.py              Download, frames, audio, transcription
|   |   +-- visual_analysis.py    Combined visual + deepfake (Claude vision)
|   |   +-- fact_check.py         Pipeline orchestrator + Claude reasoner
|   |   +-- web_search.py         Multi-provider parallel search
|   |   +-- reverse_image_search.py  imgbb + Google Lens
|   |   +-- subscription.py       Rate limiting + scan history
|   +-- evals/                 Evaluation harness (dataset + scoring)
|       +-- dataset.json         15 test cases with expected verdicts
|       +-- run_evals.py         Verdict accuracy + source quality scoring
|
+-- web/                       React web frontend (Vercel)
|   +-- src/
|       +-- App.tsx              Main app with URL validation + polling
|       +-- components/
|       |   +-- Hero.tsx           Landing page + input
|       |   +-- Results.tsx        Verdict card + claims + copy button
|       |   +-- HowItWorks.tsx     Pipeline explanation
|       +-- api.ts               Backend API client with 429 handling
|
+-- frontend/                  React Native mobile app (Expo)
    +-- app/                   Expo Router screens
    |   +-- home.tsx             Main scan screen
    |   +-- results.tsx          Results display
    |   +-- login.tsx            Authentication
    |   +-- settings.tsx         Account + subscription
    +-- components/
        +-- AuthContext.tsx       JWT auth state management
```

---

## Evaluation

The project includes an evaluation harness (`backend/evals/`) with 15 test cases covering true claims, false claims, partially true content, and control cases. Each test case has an expected verdict and is scored on two things:

- **Verdict accuracy** - 1.0 for exact match, 0.5 for adjacent verdict (e.g., "Mostly False" when expected "False"), 0.0 otherwise.
- **Source quality** - Binary: 1 if at least one real source was cited, 0 if not.

This lets me measure whether code changes improve or hurt fact-checking quality.

---

## Performance Optimizations

The scan pipeline went through several rounds of optimization to bring scan times from 10+ minutes down to about 2 minutes on free infrastructure:

- Subtitles are checked before video download (saves 30-60s when available)
- Audio transcription capped at 120 seconds (2 chunks instead of 5+)
- Visual analysis and deepfake detection merged into a single LLM call
- Search query extraction uses Claude Haiku (5x faster than Sonnet for this task)
- Web search starts in parallel with video analysis when subtitles are found early
- Video download timeout reduced from 120s to 60s per strategy
- Frame count reduced from 8 to 5, image resolution from 768px to 512px
- Redundant audio format conversions eliminated (straight to WAV)

---

## Running Locally

<details>
<summary>Click to expand local development setup</summary>

### Prerequisites

| Tool | Purpose | Install |
|---|---|---|
| Python 3.11 | Backend runtime | `winget install Python.Python.3.11` |
| Node 20+ | Frontend / Metro bundler | `winget install OpenJS.NodeJS` |
| Yarn | Expo package manager | `npm install -g yarn` |
| ffmpeg | Video/audio extraction | `winget install Gyan.FFmpeg` |

### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

Create `backend/.env`:
```ini
MONGO_URL="mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=veritas"
DB_NAME=veritas
ANTHROPIC_API_KEY=sk-ant-your-key-here
JWT_SECRET=pick-a-long-random-string
TAVILY_API_KEY=tvly-dev-...
```

Run:
```bash
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Web Frontend

```bash
cd web
npm install
npm run dev
```

### Mobile App

```bash
cd frontend
yarn install
npx expo start
```

Scan the QR code with Expo Go on your phone (must be on the same WiFi).

</details>

---

## Limitations & Honest Assessment

This is a student project, not a production fact-checking service. Some honest limitations:

- **Speed depends on free infrastructure** - Render's free tier sleeps after 15 minutes of inactivity. First scan after wake-up is the slowest.
- **Audio transcription uses Google's free STT** - It struggles with heavy background music, non-English speech, and heavily compressed audio.
- **AI can make mistakes** - Claude is powerful but not infallible. The verdict should be a starting point for critical thinking, not the final word.
- **Platform blocks** - YouTube frequently blocks downloads from cloud servers. TikTok works most reliably.
- **120-second audio cap** - Longer videos only have their first two minutes transcribed. This is a tradeoff between speed and completeness.

---

## Future Improvements

- **Paid STT integration** - Switching to Deepgram or AssemblyAI would cut transcription from ~15 seconds to ~2 seconds and add non-English support.
- **Real worker queue** - Replace the in-process background tasks with Celery or arq + Redis so scans survive server restarts and can scale horizontally.
- **Per-claim source chips in mobile UI** - Claims already carry source arrays but the mobile app doesn't render them as tappable links yet.
- **Multi-language support** - Currently only optimized for English. Adding language detection and multilingual STT would help a lot.
- **iOS App Store release** - Requires the $99/year Apple Developer Program. For now, iOS users can run it via Expo Go on the same WiFi.

---

## What I Learned

Building Veritas taught me how to design and optimize a real async pipeline, work with multiple AI APIs, deal with the messiness of real-world video processing (codec issues, platform blocks, rate limits), deploy across free-tier infrastructure, and think critically about the difference between "AI says it's true" and "here are the sources, decide for yourself."

The hardest part wasn't the AI. It was making the whole thing fast enough to actually use without spending any money.

---

*Built by Stanislav Vynnytskyi as a portfolio project, 2026.*
