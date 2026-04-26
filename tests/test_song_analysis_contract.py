from pathlib import Path

from models.song import Song, build_song_analysis


def test_build_song_analysis_exposes_per_stem_section_features() -> None:
    meta_path = Path(__file__).resolve().parents[1] / "data" / "output"
    song = Song(song_id="Cinderella - Ella Lee", base_dir=str(meta_path))

    analysis = build_song_analysis(song)

    assert analysis.beats_available is True
    assert analysis.sections_available is True
    assert analysis.features_available is True
    assert analysis.hints_available is True
    assert analysis.global_energy.get("energy_trend") == "wave"

    first_section = analysis.sections[0]
    assert first_section.name == "Intro"
    assert first_section.start_bar == 1
    assert first_section.start_beat == 1

    verse = next(section for section in analysis.sections if section.name == "Verse")
    assert verse.energy.get("trend") in {"build", "wave", "release"}
    assert verse.energy.get("level") in {"low", "medium", "high"}
    assert verse.events