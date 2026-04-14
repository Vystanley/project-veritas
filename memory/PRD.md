# Veritas AI Fact-Checker — Product Requirements Document

## Original Problem Statement
Mobile app serving as an AI fact-checker for short videos from social media platforms (TikTok, Instagram Reels, YouTube Shorts). Users share a video link, the app analyzes content for truthfulness and validity.

## Core Requirements
- **Input**: Paste a video URL from TikTok, Instagram, YouTube Shorts, etc.
- **Output**: Fact-check analysis with verdict, confidence, claims breakdown, sources, deepfake detection.
- **Auth**: JWT-based authentication with legal consent + email verification (OTP).
- **Monetization**: Free (3 scans/week), Premium Monthly ($13.99/mo), Annual ($119/yr).
- **UI**: Dark theme with dark blue color scheme.

## Architecture
```
/app
├── backend/
│   ├── server.py          # FastAPI - all routes + pipeline + web search + global error handler
│   ├── .env               # MONGO_URL, DB_NAME, EMERGENT_LLM_KEY, JWT_SECRET, STRIPE_API_KEY
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── _layout.tsx          # Root navigator, AuthProvider
│   │   ├── index.tsx            # Auth screen (Login/Register + legal consent)
│   │   ├── verify-email.tsx     # 6-digit OTP verification screen
│   │   ├── home.tsx             # URL input with validation, scan counter, upgrade modal
│   │   ├── results.tsx          # Analysis results: deepfake, claims, clickable sources
│   │   └── settings.tsx         # Account management, subscription, referrals
│   └── components/
│       └── AuthContext.tsx       # Auth state + error parsing helper
└── memory/PRD.md
```

## Key Technical Stack
- **Backend**: FastAPI, Python, MongoDB (motor), JWT auth
- **Frontend**: Expo (React Native), TypeScript, Expo Router
- **Video Pipeline**: yt-dlp (--impersonate chrome, --js-runtimes node, retry strategies), ffmpeg (auto-install)
- **AI**: OpenAI GPT-5.2 (fact-checking + deepfake vision + search query extraction), OpenAI Whisper (transcription) via Emergent LLM Key
- **Real-time Search**: DuckDuckGo Search (news + text), GPT-powered query extraction
- **Payments**: Stripe via emergentintegrations

## DB Schema
- **users**: id, name, email, password_hash, email_verified, consent_accepted, created_at
- **verification_codes**: user_id, email, code, created_at, expires_at
- **subscriptions**: user_id, plan, started_at, expires_at, bonus_scans
- **scan_logs**: user_id, video_url, check_id, created_at
- **referrals**: user_id, code, referred_users, bonus_scans_earned
- **deleted_accounts**: email, deleted_at, user_id (abuse prevention, 30-day cooldown)
- **payment_transactions**: session_id, user_id, plan, amount, status

---

## Completed Work

### V1-V4 (Previous Sessions)
- Full-stack app with JWT auth, legal consent, subscription model, Stripe, referral system, account management

### V5 — Pipeline Fix + Deepfake
- Fixed core video pipeline, multi-strategy download (TikTok full pipeline + YouTube subtitle fallback)
- Deepfake analysis with GPT-5.2 Vision via ImageContent

### V6 — Bug Fixes (Session 2)
- Fixed "[object Object]" error display with RequestValidationError handler
- Real-time AI with DuckDuckGo web search
- Fixed PRO upgrade button freeze with Linking.openURL
- Email validation (regex) on frontend + backend
- Account abuse prevention (deleted_accounts collection, 30-day cooldown)
- Email verification flow (OTP, mock mode for dev, ready for Resend integration)

### V7 — Structural Fixes (Current Session, 2026-03-07)
1. **Frontend URL Validation**: Real-time regex validation on URL input. Analyze button disabled until valid https:// URL entered. Red error text + red border when invalid. Secondary guard in handleAnalyze with Alert.
2. **Backend Global Error Handler**: `@app.exception_handler(Exception)` ensures ALL errors return JSON — never raw text. Individual try/catch blocks around every pipeline step (download, deepfake, audio, subtitles). HTTPExceptions pass through cleanly.
3. **Robust Video Download**: Retry mechanism with 2 strategies (impersonate chrome first, then plain). `ensure_ffmpeg()` auto-installs if missing. Content-Type check on frontend before JSON parse.
4. **Real-time AI Improvement**: GPT-5.2 extracts targeted search queries from transcript → DuckDuckGo news search for each → results fed as context for fact-checking.

---

## Prioritized Backlog

### P1 — Upcoming
- Integrate Resend for real email verification (currently mock mode)
- Push notifications for weekly scan reset
- RevenueCat integration for in-app purchases (iOS/Android)

### P2 — Planned
- Share fact-check results as shareable image cards
- Instagram support improvement (cookies/auth approach)

### P3 — Future
- Refactor server.py into modules (routes, services, models)
- Scan history page
- Multi-language support
- Production hardening & error monitoring
