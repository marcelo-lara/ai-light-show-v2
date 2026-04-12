import json
from pathlib import Path
from types import SimpleNamespace

from backend.api.state.song_payload import build_song_analysis_payload, parse_song_events


def test_parse_song_events_drops_evidence_ref_and_sorts(tmp_path: Path) -> None:
    events_path = tmp_path / "song_event_timeline.json"
    events_path.write_text(json.dumps({
        "events": [
            {
                "id": "later",
                "type": "impact_hit",
                "start_time": 4.0,
                "end_time": 4.5,
                "confidence": 0.8,
                "intensity": 0.9,
                "section_id": "section-002",
                "section_name": "Peak",
                "provenance": "machine-only",
                "summary": "Later event",
                "created_by": "classifier",
                "evidence_summary": "later summary",
                "lighting_hint": "later hint",
                "evidence_ref": {"machine_event_id": "later"},
            },
            {
                "id": "earlier",
                "type": "build",
                "start_time": 1.0,
                "end_time": 1.5,
                "confidence": 0.6,
                "intensity": 0.7,
                "section_id": "section-001",
                "section_name": None,
                "provenance": "review",
                "summary": "Earlier event",
                "created_by": "reviewer",
                "evidence_summary": "earlier summary",
                "lighting_hint": "earlier hint",
                "evidence_ref": {"machine_event_id": "earlier"},
            },
        ]
    }))

    parsed = parse_song_events(events_path)

    assert [item["id"] for item in parsed] == ["earlier", "later"]
    assert all("evidence_ref" not in item for item in parsed)
    assert parsed[0]["section_name"] is None


def test_build_song_analysis_payload_includes_events_from_outputs_path(tmp_path: Path) -> None:
    meta_root = tmp_path / "output"
    song_dir = meta_root / "Test Song"
    song_dir.mkdir(parents=True)
    (song_dir / "info.json").write_text(json.dumps({
        "outputs": {
            "song_event_timeline": "/data/output/Test Song/song_event_timeline.json",
        }
    }))
    (song_dir / "song_event_timeline.json").write_text(json.dumps({
        "events": [
            {
                "id": "event-001",
                "type": "impact_hit",
                "start_time": 3.703583,
                "end_time": 4.156372,
                "confidence": 0.832501,
                "intensity": 0.865001,
                "section_id": "section-001",
                "section_name": "ambient_opening",
                "provenance": "machine-only",
                "summary": "Impact hits remain single-beat candidates.",
                "created_by": "analyzer_event_classifier",
                "evidence_summary": "Accent intensity crosses the impact threshold on this beat.",
                "lighting_hint": "Use the event as a high-level musical cue, not a fixture-specific instruction.",
                "evidence_ref": {
                    "machine_event_id": "event-001",
                    "machine_file": "/data/artifacts/Test Song/event_inference/events.machine.json",
                },
            }
        ]
    }))

    manager = SimpleNamespace(state_manager=SimpleNamespace(meta_path=str(meta_root)))

    payload = build_song_analysis_payload(manager, "Test Song")

    assert payload is not None
    assert payload["events"] == [{
        "id": "event-001",
        "type": "impact_hit",
        "start_time": 3.703583,
        "end_time": 4.156372,
        "confidence": 0.832501,
        "intensity": 0.865001,
        "section_id": "section-001",
        "section_name": "ambient_opening",
        "provenance": "machine-only",
        "summary": "Impact hits remain single-beat candidates.",
        "created_by": "analyzer_event_classifier",
        "evidence_summary": "Accent intensity crosses the impact threshold on this beat.",
        "lighting_hint": "Use the event as a high-level musical cue, not a fixture-specific instruction.",
    }]