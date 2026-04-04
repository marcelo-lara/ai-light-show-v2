from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...storage.song_meta import load_json_file, song_meta_dir
from .stereo_events import build_notable_events
from .stereo_sources import discover_audio_sources, load_stereo_audio
from .stereo_windows import build_window_metrics


def analyze_stereo(song_path: str | Path, meta_path: str | Path = "/app/meta") -> dict[str, Any] | None:
    song_file = Path(song_path).expanduser().resolve()
    meta_dir = song_meta_dir(song_file, meta_path)
    features_path = meta_dir / "features.json"
    info_path = meta_dir / "info.json"
    if not features_path.exists() or not info_path.exists():
        return None
    features = load_json_file(features_path)
    info = load_json_file(info_path)
    sources = discover_audio_sources(song_file, info.get("stems_dir"))
    analysis = _analyze_sources(sources)
    features.setdefault("global", {})["stereo_analysis"] = analysis
    features_path.write_text(json.dumps(_round_floats(features), indent=2), encoding="utf-8")
    return analysis


def _analyze_sources(sources: dict[str, Path]) -> dict[str, Any]:
    source_payloads: dict[str, Any] = {}
    all_events: list[dict[str, Any]] = []
    for source, path in sources.items():
        audio, sample_rate, is_stereo = load_stereo_audio(path)
        if not is_stereo or audio is None or sample_rate is None:
            source_payloads[source] = {"available": path.exists(), "stereo": False, "event_count": 0, "notable_events": []}
            continue
        events = build_notable_events(source, build_window_metrics(audio, sample_rate))
        source_payloads[source] = {"available": True, "stereo": True, "event_count": len(events), "notable_events": events}
        all_events.extend(events)
    stems = {key: value for key, value in source_payloads.items() if key != "mix"}
    return {
        "summary": {
            "source_count": len(source_payloads),
            "stereo_source_count": sum(1 for payload in source_payloads.values() if payload["stereo"]),
            "event_count": len(all_events),
            "allowed_tags": [
                "attack_left",
                "attack_right",
                "echo_left",
                "echo_right",
                "low_end_left",
                "low_end_right",
                "percussion_left",
                "percussion_right",
                "ambience_left",
                "ambience_right",
                "split_texture",
                "centered",
            ],
        },
        "mix": source_payloads.get("mix", {"available": False, "stereo": False, "event_count": 0, "notable_events": []}),
        "notable_events": sorted(all_events, key=lambda event: (float(event["start_s"]), str(event["source"]))),
        "stems": stems,
    }


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    return value