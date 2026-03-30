from __future__ import annotations

from typing import Any


def resolve_fixture_roles(fixtures: list[Any], pois: list[dict[str, Any]], supported_effects) -> dict[str, Any]:
    pars = [fixture.id for fixture in fixtures if fixture.id.startswith("parcan_") and {"full", "flash", "blackout"}.issubset(supported_effects(fixture))]
    orbiters = [fixture.id for fixture in fixtures if "orbit" in supported_effects(fixture)]
    movers = [fixture.id for fixture in fixtures if "move_to_poi" in supported_effects(fixture)]
    if len(pars) < 2:
        raise ValueError("draft_helper_requires_parcans")
    if not movers:
        raise ValueError("draft_helper_requires_movers")
    poi_by_fixture = {
        fixture.id: [str(poi.get("id")) for poi in pois if fixture.id in (poi.get("fixtures") or {})]
        for fixture in fixtures
    }
    return {
        "pars": pars,
        "orbiters": orbiters or movers,
        "movers": movers,
        "poi_by_fixture": poi_by_fixture,
    }


def select_orbit_pair(fixture_id: str, poi_by_fixture: dict[str, list[str]]) -> tuple[str, str] | None:
    preferred = {
        "mini_beam_prism_l": ["wall", "table", "piano", "sofa", "ceiling_station"],
        "mini_beam_prism_r": ["piano", "table", "wall", "sofa", "ceiling_station"],
    }.get(fixture_id, ["table", "piano", "wall", "sofa", "ceiling_station"])
    available = [poi for poi in preferred if poi in (poi_by_fixture.get(fixture_id) or [])]
    if len(available) < 2:
        return None
    return (available[0], available[1])