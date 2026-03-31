from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from src.musical_structure.compare import compare_beats
from src.musical_structure.io import dump_json
from src.musical_structure.registry import models_for


def test_find_chords_cli() -> None:
    if os.environ.get("ANALYZER_RUN_MUSICAL_STRUCTURE_TESTS") != "1":
        pytest.skip("Set ANALYZER_RUN_MUSICAL_STRUCTURE_TESTS=1 to run musical structure integration tests")
    if not models_for("find_chords"):
        pytest.skip("No chord models configured")
    analyzer_dir = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(analyzer_dir)}
    subprocess.run(
        [
            "python",
            "analyze_song.py",
            "--song",
            "Yonaka - Seize the Power.mp3",
            "--find-chords",
            "--beats-output-name",
            "test.beats.json",
        ],
        cwd=analyzer_dir,
        env=env,
        check=True,
    )
    song_dir = analyzer_dir / "meta" / "Yonaka - Seize the Power"
    comparison = compare_beats(song_dir / "beats.json", song_dir / "test.beats.json")
    dump_json(song_dir / "test.beats.compare.json", comparison)
    assert (song_dir / "test.beats.json").exists()
    assert 0.0 <= float(comparison["error_rate"]) <= 1.0