from __future__ import annotations

from typing import Any, Dict


def _fixture_capabilities(fixture) -> Dict[str, Any]:
    ftype = str(fixture.type or "").lower()
    capabilities: Dict[str, Any] = {}
    if "moving" in ftype and "head" in ftype:
        capabilities["pan_tilt"] = True
    if "rgb" in ftype or {"red", "green", "blue"}.issubset(set((fixture.channels or {}).keys())):
        capabilities["rgb"] = True
    return capabilities


def _read_logical_values(fixture, universe) -> Dict[str, int]:
    logical_values: Dict[str, int] = {}
    channel_types = fixture.meta.get("channel_types", {})
    for channel_name, channel_type in channel_types.items():
        if channel_type == "position_16bit":
            msb_key, lsb_key = f"{channel_name}_msb", f"{channel_name}_lsb"
            if msb_key in fixture.channels and lsb_key in fixture.channels:
                msb_idx = int(fixture.channels[msb_key]) - 1
                lsb_idx = int(fixture.channels[lsb_key]) - 1
                if 0 <= msb_idx < len(universe) and 0 <= lsb_idx < len(universe):
                    logical_values[channel_name] = (int(universe[msb_idx]) << 8) | int(universe[lsb_idx])
            continue

        target_channel_name = channel_type
        if target_channel_name in fixture.channels:
            idx = int(fixture.channels[target_channel_name]) - 1
            if 0 <= idx < len(universe):
                logical_values[channel_name] = int(universe[idx])
    return logical_values


def build_fixtures_payload(manager, universe) -> Dict[str, Dict[str, Any]]:
    fixtures = {}
    for fixture in manager.state_manager.fixtures:
        fixtures[fixture.id] = {
            "id": fixture.id,
            "name": fixture.name,
            "type": fixture.type,
            "armed": bool(manager.fixture_armed.get(fixture.id, True)),
            "values": _read_logical_values(fixture, universe),
            "capabilities": _fixture_capabilities(fixture),
        }
    return fixtures
