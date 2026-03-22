import json
from pathlib import Path

from backend.store.state import StateManager

EFFECT_START_S = 1.0
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = WORKSPACE_ROOT / "backend"
FIXTURES_PATH = BACKEND_PATH / "fixtures" / "fixtures.json"

PARCAN_BASE = {"red": 64, "green": 32, "blue": 16}
PARCAN_SETUP = [{"time": 0.0, "effect": "full", "duration": 0.25, "data": PARCAN_BASE}]
POIS = [
    {"id": "target", "fixtures": {"mini_beam_prism_l": {"pan": 12000, "tilt": 28000}, "head_el150": {"pan": 18000, "tilt": 32000}}},
    {"id": "subject", "fixtures": {"mini_beam_prism_l": {"pan": 26000, "tilt": 32000}, "head_el150": {"pan": 30000, "tilt": 36000}}},
    {"id": "start", "fixtures": {"mini_beam_prism_l": {"pan": 4000, "tilt": 8000}, "head_el150": {"pan": 6000, "tilt": 10000}}},
    {"id": "end", "fixtures": {"mini_beam_prism_l": {"pan": 42000, "tilt": 20000}, "head_el150": {"pan": 44000, "tilt": 22000}}},
]


def build_state_manager() -> StateManager:
    songs_path = Path("/app/songs") if Path("/app/songs").exists() else BACKEND_PATH / "songs"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else BACKEND_PATH / "cues"
    meta_path = Path("/app/meta") if Path("/app/meta").exists() else BACKEND_PATH / "meta"
    return StateManager(BACKEND_PATH, songs_path, cues_path, meta_path)


def _load_fixture_entries() -> list[dict]:
    with open(FIXTURES_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_template_effects(template_name: str) -> list[str]:
    template_path = BACKEND_PATH / "fixtures" / f"{template_name}.json"
    with open(template_path, "r", encoding="utf-8") as handle:
        return [str(effect).strip().lower() for effect in json.load(handle).get("effects", []) if str(effect).strip()]


def effect_cases() -> list[dict]:
    template_configs = {
        "fixture.parcan.rgb_gen": {
            "flash": {"duration": 0.5, "data": {}},
            "strobe": {"duration": 0.5, "data": {"rate": 12.0}, "preview_base": PARCAN_BASE, "setup": PARCAN_SETUP},
            "fade_in": {"duration": 0.5, "data": {"red": 90, "green": 40, "blue": 10}},
            "full": {"duration": 0.25, "data": {"red": 25, "green": 50, "blue": 75}},
        },
        "fixture.parcan.rgb_proton": {
            "flash": {"duration": 0.5, "data": {}},
            "strobe": {"duration": 0.5, "data": {"rate": 12.0}, "preview_base": PARCAN_BASE, "setup": PARCAN_SETUP},
            "fade_in": {"duration": 0.5, "data": {"red": 90, "green": 40, "blue": 10}},
            "full": {"duration": 0.25, "data": {"red": 25, "green": 50, "blue": 75}},
        },
        "fixture.moving_head.mini_beam_prism": {
            "full": {"duration": 0.25, "data": {}},
            "strobe": {"duration": 0.5, "data": {"rate": 12.0}},
            "flash": {"duration": 0.5, "data": {}},
            "fade_in": {"duration": 0.5, "data": {"dim": 180}},
            "seek": {"duration": 0.5, "data": {"subject_POI": "subject", "start_POI": "start", "orbits": 1.0, "easing": "late_focus"}, "pois": POIS},
            "move_to": {"duration": 0.5, "data": {"pan": 40000, "tilt": 26000}},
            "move_to_poi": {"duration": 0.5, "data": {"target_POI": "target"}, "pois": POIS},
            "sweep": {"duration": 0.5, "data": {"subject_POI": "subject", "start_POI": "start", "end_POI": "end", "duration": 0.5, "easing": 0.5, "dimmer_easing": 0.0, "max_dim": 1.0}, "pois": POIS},
        },
        "fixture.moving_head.head_el150": {
            "full": {"duration": 0.25, "data": {}},
            "strobe": {"duration": 0.5, "data": {"rate": 12.0}},
            "flash": {"duration": 0.5, "data": {}},
            "fade_in": {"duration": 0.5, "data": {"dim": 180}},
            "seek": {"duration": 0.5, "data": {"subject_POI": "subject", "start_POI": "start", "orbits": 1.0, "easing": "late_focus"}, "pois": POIS},
            "move_to": {"duration": 0.5, "data": {"pan": 40000, "tilt": 26000}},
            "move_to_poi": {"duration": 0.5, "data": {"target_POI": "target"}, "pois": POIS},
            "sweep": {"duration": 0.5, "data": {"subject_POI": "subject", "start_POI": "start", "end_POI": "end", "duration": 0.5, "easing": 0.5, "dimmer_easing": 0.0, "max_dim": 1.0}, "pois": POIS},
        },
    }
    cases: list[dict] = []
    for fixture_entry in _load_fixture_entries():
        fixture_id = str(fixture_entry.get("id") or "").strip()
        template_name = str(fixture_entry.get("fixture") or "").strip()
        if fixture_id not in {"parcan_l", "parcan_r", "mini_beam_prism_l", "head_el150"}:
            continue
        config_map = template_configs[template_name]
        for effect in _load_template_effects(template_name):
            config = config_map[effect]
            cases.append({"fixture_id": fixture_id, "effect": effect, **config})
    return cases


def case_id(case: dict) -> str:
    return f"{case['fixture_id']}:{case['effect']}"


def apply_preview_setup(state_manager: StateManager, case: dict) -> None:
    fixture = next(item for item in state_manager.fixtures if item.id == case["fixture_id"])
    for channel_name, value in case.get("preview_base", {}).items():
        state_manager.editor_universe[fixture.absolute_channels[channel_name] - 1] = int(value)
    if case.get("pois"):
        state_manager.poi_db.pois = case["pois"]


def cue_entries(case: dict) -> list[dict]:
    setup_entries = [dict(entry, fixture_id=case["fixture_id"]) for entry in case.get("setup", [])]
    effect_entry = {
        "time": EFFECT_START_S,
        "fixture_id": case["fixture_id"],
        "effect": case["effect"],
        "duration": case["duration"],
        "data": case["data"],
    }
    return setup_entries + [effect_entry]