from types import SimpleNamespace

import pytest

from api.intents.llm.poi_context import build_poi_inventory_payload


@pytest.mark.asyncio
async def test_build_poi_inventory_payload_summarizes_fixture_coverage():
    manager = SimpleNamespace(
        state_manager=SimpleNamespace(
            get_pois=_async_return(
                [
                    {"id": "table", "name": "Table", "fixtures": {"head_el150": {"pan": 1, "tilt": 2}}},
                    {"id": "piano", "name": "Piano", "fixtures": {"head_el150": {"pan": 3, "tilt": 4}, "mini_beam_prism_l": {"pan": 5, "tilt": 6}}},
                ]
            )
        )
    )

    payload = await build_poi_inventory_payload(manager)

    assert payload == {
        "pois": [
            {"id": "piano", "name": "Piano", "fixture_ids": ["head_el150", "mini_beam_prism_l"], "fixture_target_count": 2},
            {"id": "table", "name": "Table", "fixture_ids": ["head_el150"], "fixture_target_count": 1},
        ],
        "answer": "Available POIs: piano, table.",
    }


def _async_return(value):
    async def _inner():
        return value

    return _inner