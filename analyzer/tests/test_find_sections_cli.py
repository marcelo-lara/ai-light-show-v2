from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from src.musical_structure.compare import compare_sections
from src.musical_structure.io import dump_json
from src.musical_structure.registry import models_for


def test_find_sections_cli() -> None:
    if os.environ.get("ANALYZER_RUN_MUSICAL_STRUCTURE_TESTS") != "1":
        pytest.skip("Set ANALYZER_RUN_MUSICAL_STRUCTURE_TESTS=1 to run musical structure integration tests")
    if not models_for("find_sections"):
        pytest.skip("No section models configured")
    analyzer_dir = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(analyzer_dir)}
    subprocess.run(
        [
            "python",
            "analyze_song.py",
            "--song",
            "Yonaka - Seize the Power.mp3",
            "--find-sections",
            "--sections-output-name",
            "test.sections.json",
        ],
        cwd=analyzer_dir,
        env=env,
        check=True,
    )
    song_dir = analyzer_dir / "meta" / "Yonaka - Seize the Power"
    comparison = compare_sections(song_dir / "sections.json", song_dir / "test.sections.json")
    dump_json(song_dir / "test.sections.compare.json", comparison)
    assert (song_dir / "test.sections.json").exists()
    assert 0.0 <= float(comparison["error_rate"]) <= 1.0