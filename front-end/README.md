# HOS Routing Platform

## Setup

```bash
cd front-end

pnpm i

cp .env.example .env

```

Set:

- Leave `VITE_API_BASE_URL` empty (recommended). Works with the Vite `/api` proxy in dev and with same-origin Django when serving the production build.
- Or set `VITE_API_BASE_URL=http://127.0.0.1:8000` to call Django directly from the Vite dev server

The map uses MapLibre with free Carto/OSM tiles. No map API token is required.

```bash
pnpm dev

```

Production build (served by Django at <http://127.0.0.1:8000/>):

```bash
pnpm build

```
