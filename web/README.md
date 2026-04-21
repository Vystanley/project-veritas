# Veritas - Web demo

Public fact-checking demo for the Veritas short-form video analyzer. Paste a
video link (TikTok, YouTube, Instagram, Facebook, X), wait ~1–3 minutes, and
get a verdict with citations.

## Stack

- **Vite + React 18 + TypeScript**
- **Tailwind CSS** - dark theme matching the mobile app
- **lucide-react** icons
- Talks to the Render-hosted Veritas API at `VITE_BACKEND_URL` via the
  `/api/fact-check/demo` endpoints (no auth, rate-limited to 3/day per IP).

## Local development

```bash
cd web
cp .env.example .env  # point VITE_BACKEND_URL at your Render URL
npm install
npm run dev
```

Open <http://localhost:5173>.

## Deploying to Vercel

1. Push this folder to GitHub (already in `Vystanley/project-veritas`).
2. On Vercel: **New Project** → import `project-veritas` → set **Root directory** to `web`.
3. Framework preset: **Vite**. Build command: `npm run build`. Output: `dist`.
4. Add env var **`VITE_BACKEND_URL`** = `https://veritas-backend-5l6r.onrender.com`.
5. Deploy.
