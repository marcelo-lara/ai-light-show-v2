import math
from typing import Any, Optional, Tuple

from store.pois import PoiStore

from .sweep_helpers import clamp_unit, parse_float


def resolve_poi_location(poi_key: Any) -> Optional[dict[str, float]]:
    needle = str(poi_key or "").strip().lower()
    if not needle:
        return None

    poi_db = PoiStore.get_instance()
    if not poi_db:
        return None

    for poi in poi_db.pois:
        if str(poi.get("id") or "").strip().lower() != needle:
            continue
        location = poi.get("location") or {}
        return {
            "x": clamp_unit(parse_float(location.get("x"), 0.0)),
            "y": clamp_unit(parse_float(location.get("y"), 0.0)),
            "z": clamp_unit(parse_float(location.get("z"), 0.0)),
        }
    return None


def estimate_pan_tilt_from_location(fixture, location: dict[str, float]) -> Tuple[Optional[int], Optional[int]]:
    poi_db = PoiStore.get_instance()
    if not poi_db:
        return None, None

    target_x = clamp_unit(parse_float(location.get("x"), 0.0))
    target_y = clamp_unit(parse_float(location.get("y"), 0.0))
    target_z = clamp_unit(parse_float(location.get("z"), 0.0))
    weight_total = 0.0
    pan_total = 0.0
    tilt_total = 0.0

    for poi in poi_db.pois:
        poi_id = str(poi.get("id") or "").strip().lower()
        if not poi_id.startswith("ref_"):
            continue
        fixtures = poi.get("fixtures") or {}
        fixture_values = next(
            (values for fixture_id, values in fixtures.items() if str(fixture_id).strip().lower() == fixture.id.lower()),
            None,
        )
        if not isinstance(fixture_values, dict):
            continue
        pan_u16 = fixture._parse_axis_target_u16("pan", fixture_values)
        tilt_u16 = fixture._parse_axis_target_u16("tilt", fixture_values)
        if pan_u16 is None or tilt_u16 is None:
            continue

        point = poi.get("location") or {}
        point_x = clamp_unit(parse_float(point.get("x"), 0.0))
        point_y = clamp_unit(parse_float(point.get("y"), 0.0))
        point_z = clamp_unit(parse_float(point.get("z"), 0.0))
        distance = math.dist((target_x, target_y, target_z), (point_x, point_y, point_z))
        if distance <= 1e-6:
            return int(pan_u16), int(tilt_u16)

        weight = 1.0 / (distance * distance)
        weight_total += weight
        pan_total += float(pan_u16) * weight
        tilt_total += float(tilt_u16) * weight

    if weight_total <= 0.0:
        return None, None
    return fixture._clamp_u16(round(pan_total / weight_total)), fixture._clamp_u16(round(tilt_total / weight_total))


def estimate_circle_pan_tilt(fixture, data: dict[str, Any], progress: float) -> Tuple[Optional[int], Optional[int]]:
    target_poi = str(data.get("target_poi") or data.get("target_POI") or data.get("poi_id") or "").strip()
    if not target_poi:
        return None, None

    center = resolve_poi_location(target_poi)
    if center is None:
        return fixture._resolve_poi_pan_tilt_u16(target_poi)

    radius = max(0.0, parse_float(data.get("radius"), 0.0))
    orbit_count = parse_float(data.get("orbits", data.get("cycles", 1.0)), 1.0)
    angle = math.tau * orbit_count * clamp_unit(progress)
    location = {
        "x": clamp_unit(center["x"] + (math.cos(angle) * radius)),
        "y": clamp_unit(center["y"] + (math.sin(angle) * radius)),
        "z": center["z"],
    }
    return estimate_pan_tilt_from_location(fixture, location)
