"""Named OpenStreetMap features around a known point. Unnamed objects are dropped."""

from __future__ import annotations

from typing import Any

from app.ingestion.http import cache_file, cached_record, request_json

ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
LICENSE = "ODbL 1.0"


def fetch_named_pois(slug: str, lat: float, lon: float, *, refresh: bool = False, radius_m: int = 6000) -> dict[str, Any]:
    path = cache_file("osm", slug)

    def load() -> dict[str, Any]:
        if not _valid(lat, lon):
            return {"slug": slug, "status": "invalid_center", "attractions": [], "license_name": LICENSE}
        query = _query(lat, lon, radius_m)
        payload = None
        last_error = "request failed"
        for endpoint in ENDPOINTS:
            try:
                payload = request_json(endpoint, params={"data": query}, timeout=40.0, attempts=1)
                break
            except RuntimeError as exc:
                last_error = str(exc)
        if payload is None:
            return {"slug": slug, "status": "error", "error": last_error, "attractions": [], "license_name": LICENSE}
        attractions = parse_elements(payload, center=(lat, lon), radius_m=radius_m)
        return {
            "slug": slug,
            "status": "ok",
            "license_name": LICENSE,
            "credit": "POI names and coordinates from OpenStreetMap contributors, ODbL 1.0.",
            "radius_m": radius_m,
            "attractions": attractions,
            "source_type": "openstreetmap",
        }

    return cached_record(path, refresh=refresh, loader=load)


def parse_elements(payload: dict[str, Any], *, center: tuple[float, float], radius_m: int) -> list[dict[str, Any]]:
    elements = payload.get("elements")
    if not isinstance(elements, list):
        return []
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            continue
        name = str(tags.get("name") or "").strip()
        if len(name) < 2 or name.isdigit():
            continue
        point = _point(element)
        if point is None or not _near(center, point, radius_m + 500):
            continue
        osm_type = str(element.get("type") or "")
        osm_id = element.get("id")
        identity = f"{osm_type}:{osm_id}"
        if identity in seen:
            continue
        seen.add(identity)
        kind = "osm_node" if osm_type == "node" else "osm_center"
        found.append(
            {
                "name": name,
                "category": _category(tags),
                "lat": point[0],
                "lon": point[1],
                "geometry_kind": "point" if osm_type == "node" else "center",
                "osm_type": osm_type,
                "osm_id": osm_id,
                "coordinate_status": kind,
                "source_refs": [
                    {
                        "source": "openstreetmap",
                        "osm_type": osm_type,
                        "osm_id": osm_id,
                        "license_name": LICENSE,
                    }
                ],
            }
        )
        if len(found) >= 15:
            break
    return found


def _query(lat: float, lon: float, radius_m: int) -> str:
    around = f"(around:{int(radius_m)},{lat:.5f},{lon:.5f})"
    return (
        "[out:json][timeout:20];("
        f'node["name"]["tourism"="attraction"]{around};'
        f'node["name"]["waterway"="waterfall"]{around};'
        f'node["name"]["historic"="monument"]{around};'
        ");out 12;"
    )


def _point(element: dict[str, Any]) -> tuple[float, float] | None:
    lat, lon = element.get("lat"), element.get("lon")
    if lat is None or lon is None:
        center = element.get("center") or {}
        lat, lon = center.get("lat"), center.get("lon")
    if not _valid(lat, lon):
        return None
    return float(lat), float(lon)


def _category(tags: dict[str, Any]) -> str:
    if tags.get("waterway") == "waterfall":
        return "waterfall"
    if tags.get("natural") == "peak":
        return "peak"
    if tags.get("historic"):
        return "historic"
    tourism = str(tags.get("tourism") or "")
    return tourism or "poi"


def _valid(lat: Any, lon: Any) -> bool:
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return -90 <= lat_f <= 90 and -180 <= lon_f <= 180


def _near(center: tuple[float, float], point: tuple[float, float], radius_m: int) -> bool:
    # Equirectangular check is only a reject bound for a bad center, not a road distance.
    from math import cos, radians

    lat_scale = 111_320
    lon_scale = 111_320 * cos(radians(center[0]))
    dy = (point[0] - center[0]) * lat_scale
    dx = (point[1] - center[1]) * lon_scale
    return (dx * dx + dy * dy) <= float(radius_m) ** 2
