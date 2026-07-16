# HOS Routing Platform

## Setup

```bash
cd front-end

pnpm i

cp .env.example .env

```

Set:

- Leave `VITE_API_BASE_URL` empty to use the Vite `/api` proxy (recommended; avoids CORS)
- Or set `VITE_API_BASE_URL=http://127.0.0.1:8000` to call Django directly

The map uses MapLibre with free Carto/OSM tiles. No map API token is required.

```bash
pnpm dev

```
