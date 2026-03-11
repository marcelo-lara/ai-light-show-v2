import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from models.fixture import Fixture, MovingHead, Parcan
from models.fixture_template import FixtureTemplate
from store.dmx_canvas import DMX_CHANNELS


def _load_templates(fixtures_dir: Path) -> Dict[str, FixtureTemplate]:
    templates: Dict[str, FixtureTemplate] = {}
    for template_file in fixtures_dir.glob("fixture.*.json"):
        try:
            with open(template_file, "r") as handle:
                template_data = json.load(handle)
            template = FixtureTemplate(**template_data)
            templates[template.id] = template
            templates[template_file.stem] = template
        except (OSError, ValueError, TypeError) as exc:
            print(f"Error loading template {template_file}: {exc}")
    return templates


def _instantiate_fixture(entry: dict, templates: Dict[str, FixtureTemplate]) -> Optional[Fixture]:
    template_key = entry.get("fixture")
    if template_key not in templates:
        print(f"Template {template_key} not found for fixture {entry.get('id')}")
        return None

    template = templates[template_key]
    fixture_id = entry.get("id")
    fixture_name = entry.get("name")
    base_channel = entry.get("base_channel", 1)
    location = entry.get("location", {})

    kwargs = {
        "id": fixture_id,
        "name": fixture_name,
        "base_channel": base_channel,
        "template": template,
        "location": location,
    }

    try:
        if template.type.lower() in {"moving_head", "moving-head"}:
            return MovingHead(**kwargs)
        return Parcan(**kwargs)
    except (ValueError, TypeError) as exc:
        print(f"Error instantiating fixture {fixture_id}: {exc}")
        return None


def load_fixtures_from_path(fixtures_path: Path) -> Tuple[List[Fixture], int]:
    fixtures_dir = fixtures_path.parent
    templates = _load_templates(fixtures_dir)

    with open(fixtures_path, "r") as handle:
        payload = json.load(handle)

    fixtures: List[Fixture] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        fixture = _instantiate_fixture(entry, templates)
        if fixture:
            fixtures.append(fixture)

    max_channel = 0
    for fixture in fixtures:
        for offset in fixture.channels.values():
            max_channel = max(max_channel, fixture.base_channel + offset)

    max_used_channel = max(0, min(DMX_CHANNELS, int(max_channel)))
    return fixtures, max_used_channel
