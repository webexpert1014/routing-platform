# HOS Routing Platform

## Setup

```bash
cd backend

uv sync

cp .env.example .env

```

Maps use free public services (Nominatim geocoding + OSRM routing). No Mapbox token is required. These public endpoints are for demo/MVP traffic only.

To serve the UI from Django, build the front-end first:

```bash
cd ../front-end

pnpm i

pnpm build

cd ../backend

```

```bash
uv run python manage.py runserver

```

Then open <http://127.0.0.1:8000/> — the API stays at `/api/trips/`. For hot-reload UI work, use `pnpm dev` in `front-end/` instead.

## Deploy on Vercel

1. Push this repo to GitHub/GitLab/Bitbucket.
2. In the [Vercel Dashboard](https://vercel.com/new) → **Add New** → **Project** → import the repo.
3. Leave **Root Directory** empty (repository root). If it was set to `backend`, clear it and redeploy.
4. Add env vars:
   - `DJANGO_SECRET_KEY` (required)
   - `DJANGO_DEBUG=false`
   - optional: `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`
5. Deploy.

Vercel installs Python deps from root `requirements.txt` using `.python-version` (3.13). `vercel.json` builds the Vite SPA into `backend/frontend_dist` and routes all traffic through `api/index.py` (Django WSGI). Same URL serves the UI and `/api/trips/`.
