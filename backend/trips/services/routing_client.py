from math import asin, cos, radians, sin, sqrt

import requests
from rest_framework.exceptions import ValidationError

GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
METERS_PER_MILE = 1609.344
OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/driving/{coordinates}"
REVERSE_GEOCODE_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "hos-routing-platform-demo/1.0 (local demo MVP)"


def fetch_route(waypoints: list[dict]) -> dict:
    if len(waypoints) < 2:
        raise ValidationError("At least two waypoints are required for routing.")
    coordinates = ";".join(f"{point['lng']},{point['lat']}" for point in waypoints)
    response = requests.get(
        OSRM_ROUTE_URL.format(coordinates=coordinates),
        headers={"User-Agent": USER_AGENT},
        params={"geometries": "geojson", "overview": "full", "steps": "false"},
        timeout=45,
    )
    if response.status_code != 200:
        raise ValidationError(f"OSRM routing failed (HTTP {response.status_code}).")
    payload = response.json()
    if payload.get("code") not in (None, "Ok"):
        raise ValidationError(
            f"OSRM routing failed ({payload.get('code') or 'unknown error'})."
        )
    return parse_osrm_route(payload)


def geocode_address(address: str) -> dict:
    results = suggest_addresses(address, limit=1)
    if not results:
        raise ValidationError(f"Could not find a location for '{address.strip()}'.")
    return results[0]


def haversine_miles(lat0: float, lng0: float, lat1: float, lng1: float) -> float:
    radius = 3958.8
    dlat = radians(lat1 - lat0)
    dlng = radians(lng1 - lng0)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat0)) * cos(radians(lat1)) * sin(dlng / 2) ** 2
    )
    return 2 * radius * asin(sqrt(a))


def parse_nominatim_results(results: list) -> list[dict]:
    parsed = []
    for place in results or []:
        label = place.get("display_name")
        if not label or "lat" not in place or "lon" not in place:
            continue
        parsed.append(
            {"label": label, "lat": float(place["lat"]), "lng": float(place["lon"])}
        )
    return parsed


def parse_osrm_route(payload: dict) -> dict:
    routes = payload.get("routes") or []
    if not routes:
        raise ValidationError("No driving route found between the given locations.")
    route = routes[0]
    legs = route.get("legs") or []
    meters = float(route.get("distance") or 0)
    seconds = float(route.get("duration") or 0)
    return {
        "coordinates": route.get("geometry", {}).get("coordinates") or [],
        "legs": [
            {
                "distance_miles": float(leg.get("distance") or 0) / METERS_PER_MILE,
                "duration_minutes": float(leg.get("duration") or 0) / 60.0,
            }
            for leg in legs
        ],
        "total_drive_minutes": seconds / 60.0,
        "total_miles": meters / METERS_PER_MILE,
    }


def point_along_line(
    coordinates: list[list[float]], target_miles: float
) -> tuple[float, float]:
    if not coordinates:
        return (0.0, 0.0)
    if target_miles <= 0:
        lng, lat = coordinates[0]
        return (lat, lng)
    traveled = 0.0
    for index in range(1, len(coordinates)):
        lng0, lat0 = coordinates[index - 1]
        lng1, lat1 = coordinates[index]
        segment_miles = haversine_miles(lat0, lng0, lat1, lng1)
        if traveled + segment_miles >= target_miles:
            ratio = (target_miles - traveled) / segment_miles if segment_miles else 0
            lat = lat0 + (lat1 - lat0) * ratio
            lng = lng0 + (lng1 - lng0) * ratio
            return (lat, lng)
        traveled += segment_miles
    lng, lat = coordinates[-1]
    return (lat, lng)


def reverse_geocode(lat: float, lng: float) -> dict:
    response = requests.get(
        REVERSE_GEOCODE_URL,
        headers={"User-Agent": USER_AGENT},
        params={"format": "json", "lat": lat, "lon": lng},
        timeout=30,
    )
    if response.status_code != 200:
        raise ValidationError(
            f"Reverse geocoding failed (HTTP {response.status_code})."
        )
    place = response.json() or {}
    label = place.get("display_name")
    if not label:
        raise ValidationError("Could not resolve a location for those coordinates.")
    return {"label": label, "lat": float(lat), "lng": float(lng)}


def suggest_addresses(address: str, limit: int = 5) -> list[dict]:
    query = address.strip()
    if not query:
        raise ValidationError("Location address cannot be empty.")
    response = requests.get(
        GEOCODE_URL,
        headers={"User-Agent": USER_AGENT},
        params={"format": "json", "limit": max(1, min(limit, 8)), "q": query},
        timeout=30,
    )
    if response.status_code != 200:
        raise ValidationError(
            f"Geocoding failed for '{query}' (HTTP {response.status_code})."
        )
    return parse_nominatim_results(response.json() or [])
