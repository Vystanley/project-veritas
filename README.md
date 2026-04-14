# Project Veritas

A fact-checking app for short-form social media video. Paste a TikTok / YouTube Shorts / Instagram Reel / Facebook / X URL, and the app downloads the video, transcribes the spoken audio, describes what's shown on screen, runs a deepfake check, searches the web for supporting sources, and returns a verdict with per-claim citations.

- **Backend:** Python 3.11, FastAPI, MongoDB Atlas, yt-dlp, ffmpeg, Claude (via Emergent LLM proxy), Tavily + DuckDuckGo + Wikipedia for web search.
- **Frontend:** React Native + Expo (Expo Go for dev, EAS Build for production).

---

## Architecture at a glance

```
Phone (Expo Go)
   │  POST /api/fact-check     →  202 { job_id }
   │  GET  /api/fact-check/{id}/status  (poll every 3s)
   ▼
FastAPI backend
   ├─ routes/            HTTP handlers (auth, fact-check, subscription, etc.)
   ├─ services/
   │    ├─ video.py             download + audio/frame extraction (yt-dlp, ffmpeg)
   │    ├─ visual_analysis.py   Claude vision → what's on screen
   │    ├─ deepfake.py          Claude vision → AI-generated flag
   │    ├─ fact_check.py        orchestrator + Claude reasoner
   │    └─ web_search.py        Tavily + Wikipedia + DuckDuckGo + Brave
   ├─ jobs.py            MongoDB-backed job queue (jobs survive restarts)
   └─ database.py        Motor async Mongo client

MongoDB Atlas (free M0 cluster)
   ├─ users
   ├─ fact_check_jobs   (TTL-indexed, auto-deletes after 1h)
   └─ scans             (history)
```

Frame extraction happens once per scan, then frames are shared across deepfake + visual analysis. Transcription runs in parallel. Sources are gated: Claude can only cite URLs that came back from real web search results — fabricated citations are dropped and logged.

---

## Prerequisites

Install on your machine (Windows instructions shown; adapt for macOS/Linux):

| Tool | Purpose | Install |
|---|---|---|
| Python 3.11 | Backend runtime | `winget install Python.Python.3.11` |
| Node 20+ | Frontend / Metro bundler | `winget install OpenJS.NodeJS` |
| Yarn | Expo / npm manager | `npm install -g yarn` |
| ffmpeg | Video/audio extraction | `winget install Gyan.FFmpeg` |
| Git | Source control | `winget install Git.Git` |

**Expo Go** app on your phone (iOS or Android) — install from App Store / Play Store. Required for live development on a real device.

**MongoDB Atlas account** — free tier M0 cluster. Sign up at <https://www.mongodb.com/cloud/atlas>.

**Tavily API key** (optional but strongly recommended) — free tier gives 1000 queries/month. Sign up at <https://app.tavily.com>. Without it, you fall back to DuckDuckGo + Wikipedia only, which returns significantly fewer sources.

**Emergent LLM key** — proxy key for Claude and Stripe. This is specific to this project (built on Emergent's platform).

---

## First-time setup

### 1. Clone and configure backend

```powershell
git clone <your repo URL>
cd "Project Veritas\backend"

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

Create `backend/.env` (copy from `.env.example` if present, or create fresh):

```ini
MONGO_URL="mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=veritas"
DB_NAME=veritas
EMERGENT_LLM_KEY=sk-emergent-...
JWT_SECRET=pick-a-long-random-string
STRIPE_API_KEY=sk_test_emergent
TAVILY_API_KEY=tvly-dev-...
# Optional: BRAVE_SEARCH_API_KEY=BSA...
# Optional (reverse image search): IMGBB_API_KEY=..., SERPAPI_API_KEY=...
```

If your Mongo password contains `@`, `:`, `/`, or other reserved URL characters, URL-encode them or reset to something alphanumeric. Bad URL-encoding is the #1 "why won't Mongo connect" cause.

Make sure `.env` is gitignored (it is — see `.gitignore`).

### 2. MongoDB Atlas network access

In the Atlas UI → **Network Access** → add your current IP, or `0.0.0.0/0` for dev-from-anywhere (not for production). Without this, every query hangs for 30 seconds and then fails.

### 3. Configure frontend

```powershell
cd "Project Veritas\frontend"
yarn install
```

Create `frontend/.env`:

```ini
EXPO_PUBLIC_BACKEND_URL=http://<YOUR_COMPUTER_LAN_IP>:8000
```

Find your LAN IP with `ipconfig` — look for `IPv4 Address` under your active adapter (Wi-Fi or Ethernet). Something like `192.168.1.42`. **Do not use `localhost` or `127.0.0.1`** — the phone can't reach those from another device.

### 4. Windows firewall

Your phone won't be able to reach port 8000 unless Windows Firewall allows it. Run **once** in an **Administrator** PowerShell:

```powershell
New-NetFirewallRule -DisplayName "Uvicorn 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## Running locally

You need **two** PowerShell windows open at once.

### Terminal 1 — backend

```powershell
cd "Project Veritas\backend"
.\.venv\Scripts\Activate.ps1
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

The `--host 0.0.0.0` is critical — it makes uvicorn listen on all interfaces, not just `127.0.0.1`. Without it, your phone can't connect.

You should see `Uvicorn running on http://0.0.0.0:8000`. Test it in a browser: <http://localhost:8000/api/health> → `{"status":"ok","service":"veritas-api"}`.

### Terminal 2 — frontend

```powershell
cd "Project Veritas\frontend"
npx expo start
```

Scan the QR code with the Expo Go app on your phone. First load can take 60-90 seconds while Metro bundles.

---

## Environment variables reference

### Backend (`backend/.env`)

| Key | Required | Notes |
|---|---|---|
| `MONGO_URL` | ✅ | Full SRV connection string from Atlas |
| `DB_NAME` | ✅ | Database name, e.g. `veritas` |
| `EMERGENT_LLM_KEY` | ✅ | Provided by Emergent — powers Claude calls |
| `JWT_SECRET` | ✅ | Random string for JWT signing |
| `STRIPE_API_KEY` | ✅ | Stripe test or live key (proxied through Emergent) |
| `TAVILY_API_KEY` | recommended | Big accuracy win. 1000 free queries/month |
| `BRAVE_SEARCH_API_KEY` | optional | Additional search provider |
| `IMGBB_API_KEY` | optional | Image host for reverse image search. Free, get at <https://api.imgbb.com/> |
| `SERPAPI_API_KEY` | optional | Google Lens reverse image search. 100 free searches/month at <https://serpapi.com/> |

### Frontend (`frontend/.env`)

| Key | Required | Notes |
|---|---|---|
| `EXPO_PUBLIC_BACKEND_URL` | ✅ | Your LAN IP + port, e.g. `http://192.168.1.42:8000` |

---

## Known Windows gotchas

These are all things that burned hours during first setup. Keeping them here so future-you doesn't re-discover them.

### 1. `asyncio.create_subprocess_exec` raises `NotImplementedError`

Under uvicorn's `--reload` event loop on Windows, `asyncio.create_subprocess_exec` is unsupported. Our `services/video.py` works around this by running every subprocess (yt-dlp, ffmpeg, ffprobe) through `asyncio.to_thread(subprocess.run)` via the `_run_subprocess` helper. **Never add a new `asyncio.create_subprocess_exec` call** — it will silently break on Windows. Use `_run_subprocess` instead.

### 2. `--ffmpeg-location` and the WinGet shim trap

`shutil.which("ffmpeg")` on Windows points to `C:\Users\<you>\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe`, which is a **shim** — not the real binary. That directory has no `ffprobe.exe`, so passing it to `yt-dlp --ffmpeg-location` breaks yt-dlp.

The fix in `services/video.py` only passes `--ffmpeg-location` when the directory contains BOTH `ffmpeg` and `ffprobe`. Otherwise it omits the flag and lets yt-dlp find them via `PATH`.

### 3. Expo `useShareIntent` stub

The `expo-share-intent` package breaks in Expo Go (it requires a dev-client build). `frontend/app/_layout.tsx` stubs out the hook so the app boots cleanly in Expo Go. When you build a dev client with EAS, un-stub it and re-enable the real hook.

### 4. PowerShell script execution policy

Fresh Windows installs block `Activate.ps1`. Fix once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 5. PowerShell command with URL

If you paste a command like `yt-dlp ... https://youtube.com/...` and hit Enter after the URL's own newline, PowerShell splits it into two commands and fails with "You must provide at least one URL". Keep the whole command on one line before pressing Enter.

### 6. `primp==1.1.2` wheel missing on Windows

The pinned `primp` version in `requirements.txt` has no Windows Python 3.11 wheel. The fix is already applied: we use unpinned `primp` so pip picks whatever works.

### 7. `emergentintegrations` is not on PyPI

It's on Emergent's private package server. That's why `pip install` uses `--extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/`.

---

## Troubleshooting

**Phone shows infinite loading spinner after login.**
Test `http://<your-IP>:8000/api/health` in the phone's browser. If that fails, either (a) uvicorn is bound to `127.0.0.1` instead of `0.0.0.0`, (b) Windows Firewall is blocking port 8000, or (c) the phone isn't on the same Wi-Fi as your computer. If `/health` works but the app still spins, Metro (Terminal 2) may have crashed — restart with `npx expo start -c`.

**"Video download failed — trying subtitle fallback" on every scan.**
Scroll up in the backend log to find the `yt-dlp strategy 1 failed (rc=...):` line. Common causes: (a) yt-dlp is outdated — run `pip install -U yt-dlp`; (b) platform is blocking the request — strategy 3 (`--impersonate chrome`) is the fallback, but it requires `curl_cffi` to work; (c) the `--ffmpeg-location` issue from section 2 above.

**Everything comes back "Unverified".**
Check the backend log for `Web search providers: DDG=X, Wikipedia=Y, Brave=Z, Tavily=W`. If Tavily=0, your `TAVILY_API_KEY` is missing or invalid. If all are 0, DuckDuckGo is rate-limiting and you need at least one API-key-based provider.

**Mongo hangs and times out.**
Your current IP isn't whitelisted in Atlas → Network Access. Or your password contains special characters that need URL-encoding. Reset to something alphanumeric.

**Results screen opens multiple times per scan.**
This was a bug — already fixed via `navigatedRef` guard in `home.tsx`. If it resurfaces, make sure any new navigation-on-completion calls go through that same guard.

---

## Project structure

```
Project Veritas/
├── backend/
│   ├── server.py              FastAPI entry point
│   ├── config.py              env vars, plans, paths
│   ├── database.py            Motor async Mongo client
│   ├── models.py              Pydantic models
│   ├── auth.py                JWT + bcrypt helpers
│   ├── jobs.py                Mongo-backed fact-check job queue
│   ├── routes/                HTTP route handlers
│   │   ├── auth.py
│   │   ├── fact_check.py
│   │   ├── subscription.py
│   │   ├── payments.py
│   │   ├── referral.py
│   │   ├── notifications.py
│   │   ├── account.py
│   │   └── health.py
│   ├── services/              business logic
│   │   ├── video.py              download + frame/audio extraction
│   │   ├── visual_analysis.py    Claude vision → on-screen content
│   │   ├── deepfake.py           Claude vision → deepfake detection
│   │   ├── fact_check.py         orchestrator + Claude reasoner
│   │   ├── web_search.py         Tavily + Wikipedia + DDG + Brave
│   │   ├── subscription.py       plan limits + scan logging
│   │   └── referral.py           referral bonus logic
│   ├── tests/
│   └── requirements.txt
│
└── frontend/
    ├── app/                   expo-router screens
    │   ├── _layout.tsx
    │   ├── home.tsx
    │   ├── results.tsx
    │   ├── login.tsx
    │   └── ...
    ├── components/
    ├── constants/
    ├── package.json
    └── .env
```

---

## What's not done yet

- **Deployment** — backend to Render, mobile app via EAS Build.
- **Per-claim source chips in the UI** — right now claims carry `sources` arrays but the UI doesn't render them as tappable chips.
- **Real tests under `backend/tests/`** — scaffolding exists, assertions mostly do not.
- **Resume interrupted scans** — jobs persist across restarts, but the pipeline coroutine doesn't resume. Would need a real worker queue (Celery / RQ / arq + Redis) for that.
