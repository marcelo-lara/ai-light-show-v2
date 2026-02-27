from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from song_metadata_mcp.index import MetadataIndexStore


@pytest.fixture()
def meta_root(tmp_path: Path) -> Path:
    song_dir = tmp_path / "Test Song"
    essentia = song_dir / "essentia"
    moises = song_dir / "moises"
    essentia.mkdir(parents=True)
    moises.mkdir(parents=True)

    (song_dir / "info.json").write_text(
        json.dumps(
            {
                "filename": "Test Song",
                "song_name": "Test Song",
                "beat_tracking": {"tempo_bpm": 120.0},
            }
        ),
        encoding="utf-8",
    )
    (song_dir / "beats.json").write_text(
        json.dumps({"beats": [1.0, 2.0, 3.0, 4.0], "downbeats": [1.0, 3.0]}),
        encoding="utf-8",
    )
    (essentia / "spectral_centroid.json").write_text(
        json.dumps(
            {
                "part": "mix",
                "sample_rate": 44100,
                "duration": 4.0,
                "times": [0.0, 1.0, 2.0, 3.0],
                "centroid": [10.0, 20.0, 30.0, 40.0],
            }
        ),
        encoding="utf-8",
    )
    (moises / "beats.json").write_text(
        json.dumps(
            [
                {"time": 1.0, "beatNum": 1},
                {"time": 2.0, "beatNum": 2},
                {"time": 3.0, "beatNum": 3},
            ]
        ),
        encoding="utf-8",
    )
    return tmp_path


def build_store(meta_root: Path, *, max_raw_points: int = 20000, default_max_points: int = 5000) -> MetadataIndexStore:
    return MetadataIndexStore(meta_root=meta_root, max_raw_points=max_raw_points, default_max_points=default_max_points)


def test_feature_discovery_and_normalization(meta_root: Path) -> None:
    store = build_store(meta_root)
    result = store.list_features("Test Song")

    assert result["ok"] is True
    features = result["data"]["features"]
    assert "analyzer.beats" in features
    assert "analyzer.downbeats" in features
    assert "essentia.spectral_centroid.centroid" in features
    assert "moises.beats.beat_num" in features


def test_time_window_slice_includes_boundaries(meta_root: Path) -> None:
    store = build_store(meta_root)
    result = store.query_feature(
        song="Test Song",
        feature="essentia.spectral_centroid.centroid",
        start_time=1.0,
        end_time=2.0,
        include_raw=True,
        mode="summary",
        max_points=100,
        time_tolerance_ms=0,
    )

    assert result["ok"] is True
    raw = result["data"]["raw"]
    assert raw["times"] == [1.0, 2.0]
    assert raw["values"] == [20.0, 30.0]


def test_exact_mode_returns_unmodified_raw(meta_root: Path) -> None:
    store = build_store(meta_root)
    result = store.query_feature(
        song="Test Song",
        feature="analyzer.beats",
        start_time=1.0,
        end_time=4.0,
        include_raw=True,
        mode="exact",
        max_points=None,
        time_tolerance_ms=0,
    )

    assert result["ok"] is True
    assert result["data"]["raw"]["times"] == [1.0, 2.0, 3.0, 4.0]


def test_summary_mode_omits_raw_by_default(meta_root: Path) -> None:
    store = build_store(meta_root)
    result = store.query_feature(
        song="Test Song",
        feature="analyzer.downbeats",
        start_time=1.0,
        end_time=3.0,
        include_raw=False,
        mode="summary",
        max_points=None,
        time_tolerance_ms=0,
    )

    assert result["ok"] is True
    assert "raw" not in result["data"]
    assert result["data"]["summary"]["points"] == 2


def test_large_exact_payload_is_rejected(meta_root: Path) -> None:
    store = build_store(meta_root, max_raw_points=2)
    with pytest.raises(Exception) as exc:
        store.query_feature(
            song="Test Song",
            feature="analyzer.beats",
            start_time=1.0,
            end_time=4.0,
            include_raw=True,
            mode="exact",
            max_points=None,
            time_tolerance_ms=0,
        )

    assert "payload_too_large" in str(exc.value)


def test_cache_invalidation_on_file_change(meta_root: Path) -> None:
    store = build_store(meta_root)

    before = store.query_feature(
        song="Test Song",
        feature="essentia.spectral_centroid.centroid",
        start_time=0.0,
        end_time=3.0,
        include_raw=True,
        mode="exact",
        max_points=None,
        time_tolerance_ms=0,
    )
    assert before["data"]["raw"]["values"][-1] == 40.0

    path = meta_root / "Test Song" / "essentia" / "spectral_centroid.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["centroid"][-1] = 99.0
    path.write_text(json.dumps(payload), encoding="utf-8")
    time.sleep(0.01)

    after = store.query_feature(
        song="Test Song",
        feature="essentia.spectral_centroid.centroid",
        start_time=0.0,
        end_time=3.0,
        include_raw=True,
        mode="exact",
        max_points=None,
        time_tolerance_ms=0,
    )

    assert after["data"]["raw"]["values"][-1] == 99.0
