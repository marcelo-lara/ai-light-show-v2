from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

from src.song_features.stereo import ALLOWED_STEREO_TAGS, analyze_stereo


def test_analyze_stereo_updates_features_with_allowed_tags(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Stereo Song.wav"
    stems_dir = tmp_path / "meta" / "Stereo Song" / "stems"
    features_path = tmp_path / "meta" / "Stereo Song" / "features.json"
    info_path = tmp_path / "meta" / "Stereo Song" / "info.json"
    stems_dir.mkdir(parents=True)
    song_path.parent.mkdir(parents=True)
    _write_stereo(song_path, _mix_signal())
    _write_stereo(stems_dir / "drums.wav", _drums_signal())
    _write_stereo(stems_dir / "bass.wav", _bass_signal())
    features_path.write_text(json.dumps({"global": {}, "sections": []}), encoding="utf-8")
    info_path.write_text(json.dumps({"stems_dir": str(stems_dir)}), encoding="utf-8")

    payload = analyze_stereo(song_path, meta_path=tmp_path / "meta")

    assert payload is not None
    assert payload["summary"]["event_count"] > 0
    assert payload["mix"]["event_count"] > 0
    assert payload["stems"]["drums"]["event_count"] > 0
    assert payload["stems"]["bass"]["event_count"] > 0
    stored = json.loads(features_path.read_text(encoding="utf-8"))
    stereo_analysis = stored["global"]["stereo_analysis"]
    assert stereo_analysis["summary"]["allowed_tags"] == sorted(ALLOWED_STEREO_TAGS, key=payload["summary"]["allowed_tags"].index)
    tags = {tag for event in stereo_analysis["notable_events"] for tag in event["tags"]}
    assert tags <= ALLOWED_STEREO_TAGS
    assert {"low_end_right", "percussion_left"} <= tags


def _write_stereo(path: Path, stereo: np.ndarray, sample_rate: int = 22050) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(stereo.T, -1.0, 1.0)
    pcm = (clipped * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def _mix_signal(sample_rate: int = 22050, duration_s: float = 2.0) -> np.ndarray:
    times = np.linspace(0.0, duration_s, int(sample_rate * duration_s), endpoint=False)
    left = 0.35 * np.sin(2 * np.pi * 4800 * times)
    left[::1800] += 0.8
    right = 0.45 * np.sin(2 * np.pi * 110 * times)
    right += 0.18 * np.sin(2 * np.pi * 900 * times) * np.linspace(1.0, 0.1, times.size)
    return np.vstack([left, right]).astype(np.float32)


def _drums_signal(sample_rate: int = 22050, duration_s: float = 2.0) -> np.ndarray:
    times = np.linspace(0.0, duration_s, int(sample_rate * duration_s), endpoint=False)
    left = np.zeros_like(times)
    left[::2205] = 1.0
    left += 0.15 * np.sin(2 * np.pi * 3500 * times)
    right = 0.03 * np.sin(2 * np.pi * 300 * times)
    return np.vstack([left, right]).astype(np.float32)


def _bass_signal(sample_rate: int = 22050, duration_s: float = 2.0) -> np.ndarray:
    times = np.linspace(0.0, duration_s, int(sample_rate * duration_s), endpoint=False)
    left = 0.04 * np.sin(2 * np.pi * 130 * times)
    right = 0.45 * np.sin(2 * np.pi * 90 * times)
    return np.vstack([left, right]).astype(np.float32)