from __future__ import annotations

from typing import Any, Dict, List

from api.intents.registry import INTENT_HANDLERS


INTENT_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "transport": [
        {"name": "transport.play", "summary": "Start playback.", "payload_keys": [], "notes": "Starts playback ticker and continuous Art-Net send."},
        {"name": "transport.pause", "summary": "Pause playback.", "payload_keys": [], "notes": "Stops playback ticker and continuous Art-Net send."},
        {"name": "transport.stop", "summary": "Stop playback and blackout output.", "payload_keys": [], "notes": "Seeks to 0 and blackouts output universe."},
        {"name": "transport.jump_to_time", "summary": "Seek to a specific time.", "payload_keys": ["time_ms"], "notes": "Time is provided in milliseconds."},
        {"name": "transport.jump_to_section", "summary": "Seek to a section start by index.", "payload_keys": ["section_index"], "notes": "Uses normalized loaded-song sections."},
    ],
    "fixture": [
        {"name": "fixture.set_arm", "summary": "Arm or disarm one fixture.", "payload_keys": ["fixture_id", "armed"], "notes": "Changes arm state only."},
        {"name": "fixture.set_values", "summary": "Apply live values to one fixture.", "payload_keys": ["fixture_id", "values"], "notes": "Updates DMX values via meta-channels or direct channels."},
        {"name": "fixture.preview_effect", "summary": "Run a temporary preview effect.", "payload_keys": ["fixture_id", "effect_id", "duration_ms", "params"], "notes": "Preview is non-persistent."},
        {"name": "fixture.stop_preview", "summary": "Stop fixture preview.", "payload_keys": [], "notes": "Currently not implemented."},
    ],
    "cue": [
        {"name": "cue.add", "summary": "Add an effect or chaser cue row.", "payload_keys": ["time", "fixture_id", "effect", "duration", "data", "chaser_id"], "notes": "Use either effect fields or chaser_id, not both."},
        {"name": "cue.update", "summary": "Update one cue row by index.", "payload_keys": ["index", "patch"], "notes": "Patch is partial cue payload."},
        {"name": "cue.delete", "summary": "Delete one cue row by index.", "payload_keys": ["index"], "notes": "Mutates the current cue sheet."},
        {"name": "cue.clear", "summary": "Clear cue rows by time range.", "payload_keys": ["from_time", "to_time"], "notes": "If to_time is omitted, clears from from_time onward."},
        {"name": "cue.apply_helper", "summary": "Generate cue rows from a helper.", "payload_keys": ["helper_id"], "notes": "Current helper id: downbeats_and_beats."},
    ],
    "chaser": [
        {"name": "chaser.apply", "summary": "Persist a chaser row to the cue sheet.", "payload_keys": ["chaser_id", "start_time_ms", "repetitions"], "notes": "Writes chaser-backed cue data."},
        {"name": "chaser.preview", "summary": "Preview a chaser temporarily.", "payload_keys": ["chaser_id", "start_time_ms", "repetitions"], "notes": "Non-persistent preview."},
        {"name": "chaser.stop_preview", "summary": "Stop active chaser preview.", "payload_keys": [], "notes": "No-op if preview is not active."},
        {"name": "chaser.start", "summary": "Start a runtime chaser instance.", "payload_keys": ["chaser_id", "start_time_ms", "repetitions"], "notes": "Starts an instance rather than writing cue rows."},
        {"name": "chaser.stop", "summary": "Stop a runtime chaser instance.", "payload_keys": ["instance_id"], "notes": "Stops a started chaser instance."},
        {"name": "chaser.list", "summary": "List available chaser definitions.", "payload_keys": [], "notes": "Returns chaser definitions via event."},
    ],
    "poi": [
        {"name": "poi.create", "summary": "Create a POI.", "payload_keys": ["id", "label", "x", "y", "z", "fixtures"], "notes": "Payload is stored directly in the POI database."},
        {"name": "poi.update", "summary": "Update a POI by id.", "payload_keys": ["id"], "notes": "Additional payload keys are applied as a patch."},
        {"name": "poi.delete", "summary": "Delete a POI by id.", "payload_keys": ["id"], "notes": "Removes the POI from storage."},
        {"name": "poi.update_fixture_target", "summary": "Update a fixture target inside a POI.", "payload_keys": ["poi_id", "fixture_id", "pan", "tilt"], "notes": "Pan and tilt use u16-style values."},
    ],
    "llm": [
        {"name": "llm.send_prompt", "summary": "Start an LLM chat request.", "payload_keys": ["prompt"], "notes": "Streams lookup status and assistant output."},
        {"name": "llm.cancel", "summary": "Cancel the active LLM request.", "payload_keys": [], "notes": "Cancels the active upstream LLM task if one exists."},
    ],
}


def build_intent_catalog_payload() -> Dict[str, Any]:
    registered = {
        intent_name
        for handlers_by_domain in INTENT_HANDLERS.values()
        for intent_name in handlers_by_domain.keys()
    }
    documented = {
        item["name"]
        for intents in INTENT_CATALOG.values()
        for item in intents
    }
    domains = [
        {"domain": domain, "intents": list(intents)}
        for domain, intents in INTENT_CATALOG.items()
    ]
    return {
        "domains": domains,
        "intent_count": len(documented),
        "undocumented_intents": sorted(registered - documented),
        "extra_documented_intents": sorted(documented - registered),
    }