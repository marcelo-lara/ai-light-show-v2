from __future__ import annotations
from typing import Any, Dict, Union

from models.fixtures.effects import REGISTRY
from models.fixtures.rgb_utils import rgb_to_hex


def _fixture_capabilities(fixture) -> Dict[str, Any]:
    capabilities: Dict[str, Any] = {}
    for mc in fixture.meta_channels.values():
        if mc.kind == "u16" and mc.label.lower() in ["pan", "tilt"]:
            capabilities["pan_tilt"] = True
        if mc.kind == "rgb":
            capabilities["rgb"] = True
    return capabilities


def _read_logical_values(fixture, universe) -> Dict[str, Union[int, str]]:
    logical_values: Dict[str, Union[int, str]] = {}

    for mc_id, mc in fixture.meta_channels.items():
        if mc.kind == "u16" and mc.channels and len(mc.channels) == 2:
            msb_idx = fixture.absolute_channels[mc.channels[0]] - 1
            lsb_idx = fixture.absolute_channels[mc.channels[1]] - 1
            if 0 <= msb_idx < len(universe) and 0 <= lsb_idx < len(universe):
                val = (int(universe[msb_idx]) << 8) | int(universe[lsb_idx])
                logical_values[mc_id] = val
        elif mc.kind == "rgb" and mc.channels and len(mc.channels) >= 3:
            r_idx = fixture.absolute_channels[mc.channels[0]] - 1
            g_idx = fixture.absolute_channels[mc.channels[1]] - 1
            b_idx = fixture.absolute_channels[mc.channels[2]] - 1
            if 0 <= r_idx < len(universe) and 0 <= g_idx < len(universe) and 0 <= b_idx < len(universe):
                red = int(universe[r_idx])
                green = int(universe[g_idx])
                blue = int(universe[b_idx])
                logical_values[mc_id] = rgb_to_hex(red, green, blue)
        elif mc.kind == "enum" and mc.mapping and mc.channel:
            ch_idx = fixture.absolute_channels[mc.channel] - 1
            if 0 <= ch_idx < len(universe):
                val = int(universe[ch_idx])
                # Find mapping label if possible, else return raw value
                mapping = fixture.mappings.get(mc.mapping, {})
                label = next((k for k, v in mapping.items() if v == val), val)
                logical_values[mc_id] = label
        elif mc.channel:
            ch_idx = fixture.absolute_channels[mc.channel] - 1
            if 0 <= ch_idx < len(universe):
                logical_values[mc_id] = int(universe[ch_idx])

    return logical_values


def build_fixtures_payload(manager, universe) -> Dict[str, Any]:
    fixtures = {}
    for fixture in manager.state_manager.fixtures:
        supported_effects = REGISTRY.get_supported_effect_metadata(fixture)
        fixtures[fixture.id] = {
            "id": fixture.id,
            "name": fixture.name,
            "type": fixture.type,
            "armed": bool(manager.fixture_armed.get(fixture.id, True)),
            "values": _read_logical_values(fixture, universe),
            "capabilities": _fixture_capabilities(fixture),
            "meta_channels": {k: v.model_dump() for k, v in fixture.meta_channels.items()},
            "mappings": fixture.mappings,
            "supported_effects": supported_effects,
        }
    return fixtures
