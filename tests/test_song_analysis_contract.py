from pathlib import Path

from models.song import Song, build_song_analysis


def test_build_song_analysis_exposes_per_stem_section_features() -> None:
    meta_path = Path("/home/darkangel/ai-light-show-v2/analyzer/meta")
    song = Song(song_id="Yonaka - Seize the Power", base_dir=str(meta_path))

    analysis = build_song_analysis(song)

    assert analysis.beats_available is True
    assert analysis.sections_available is True
    assert analysis.features_available is True
    assert {"drums", "vocals"}.issubset(set(analysis.available_parts))

    verse = next(section for section in analysis.sections if section.name == "Verse")
    assert verse.start_bar == 32
    assert verse.start_beat == 1
    assert verse.energy.get("trend") == "swell"
    assert "vocals" in verse.stem_accents
    assert verse.stem_accents["vocals"]
    assert verse.low_windows