from types import SimpleNamespace

from api.intents.llm.fixture_position_context import build_fixture_positions_payload


def test_build_fixture_positions_payload_includes_directional_labels_and_selector_terms():
    manager = SimpleNamespace(
        state_manager=SimpleNamespace(
            fixtures=[
                SimpleNamespace(id="parcan_l", name="ParCan L", type="parcan", location={"x": 0.25, "y": 0.0, "z": 0.0}),
                SimpleNamespace(id="head_el150", name="Head EL-150", type="moving_head", location={"x": 0.4, "y": 0.0, "z": 0.0}),
            ]
        )
    )

    payload = build_fixture_positions_payload(manager)

    assert payload["fixtures"] == [
        {
            "id": "head_el150",
            "name": "Head EL-150",
            "type": "moving_head",
            "location": {"x": 0.4, "y": 0.0, "z": 0.0},
            "position_labels": {"x": "center", "y": "back", "z": "floor"},
            "selector_terms": ["150", "back", "center", "el", "el150", "floor", "head", "moving"],
        },
        {
            "id": "parcan_l",
            "name": "ParCan L",
            "type": "parcan",
            "location": {"x": 0.25, "y": 0.0, "z": 0.0},
            "position_labels": {"x": "left", "y": "back", "z": "floor"},
            "selector_terms": ["back", "floor", "l", "left", "parcan"],
        },
    ]
    assert payload["answer"] == "Available fixture positions: head_el150, parcan_l."