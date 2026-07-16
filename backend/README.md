# HOS Routing Platform

## Setup

```bash
cd backend

uv sync

cp .env.example .env

```

Maps use free public services (Nominatim geocoding + OSRM routing). No Mapbox token is required. These public endpoints are for demo/MVP traffic only.

```bash
uv run python manage.py runserver

```
