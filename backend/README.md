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
