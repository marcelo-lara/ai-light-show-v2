from __future__ import annotations

import json
import sys
from pathlib import Path

import analyze_song


def test_run_generate_md_for_writes_song_markdown(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_meta_dir = meta_root / "Test Song"
    song_meta_dir.mkdir(parents=True)
    (song_meta_dir / "music_feature_layers.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "title": "Test Song",
                    "artist": "Test Artist",
                    "duration_s": 50.14,
                    "bpm": 120.0,
                    "time_signature": "4/4",
                    "key": "Am",
                },
                "layers": {"energy": {"global_energy": {"mean": 0.5, "peak": 1.2, "energy_trend": "wave"}}},
                "energy_profile": {
                    "energy_trend": "wave",
                    "dynamic_range": 1.2,
                    "transient_density": 0.45,
                    "loudness_mean": 0.5,
                    "loudness_peak": 1.2,
                    "loudness_percentile_90": 1.0,
                    "onset_count": 12,
                    "onset_density_per_minute": 14.4,
                    "flux_mean": 0.42,
                    "flux_peak": 1.8,
                    "brightness_trend": "rising",
                    "centroid_mean": 0.18,
                    "centroid_peak": 0.31,
                    "centroid_summary": "Centroid stays balanced overall, peaks at 0.310, and trends rising.",
                    "flux_summary": "Onset flux is spiky with mean 0.420, peak 1.800, and 12 detected onset anchors.",
                },
                "timeline": {
                    "sections": [
                        {"name": "Intro", "start_s": 1.36, "end_s": 35.82},
                        {"name": "Instrumental", "start_s": 35.82, "end_s": 50.14},
                    ]
                },
                "structure_summary": "2 sections with an overall wave energy trend, rising brightness arc, and 12 detected onset anchors.",
                "mapping_rules": ["Bass -> dimmer pulses"],
                "section_cards": [
                    {
                        "section_name": "Intro",
                        "start_s": 1.36,
                        "end_s": 35.82,
                        "music_description": "Intro stays restrained.",
                        "energy_description": "Low energy with a hold contour, loudness peak 0.400, centroid mean 0.110.",
                        "energy_profile": {"level": "low", "trend": "hold", "loudness_peak": 0.4, "centroid_mean": 0.11, "flux_mean": 0.21},
                        "visual_implications": ["Narrow the rig"],
                    },
                    {
                        "section_name": "Instrumental",
                        "start_s": 35.82,
                        "end_s": 50.14,
                        "music_description": "Instrumental opens the groove.",
                        "energy_description": "High energy with a push contour, loudness peak 1.200, centroid mean 0.220.",
                        "energy_profile": {"level": "high", "trend": "push", "loudness_peak": 1.2, "centroid_mean": 0.22, "flux_mean": 0.61},
                        "visual_implications": ["Use phrase-led motion"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    output_path = analyze_song.run_generate_md_for(song_path, meta_path=meta_root)

    assert output_path == song_meta_dir / "lighting_score.md"
    assert output_path.read_text(encoding="utf-8") == (
        "# Test Song - Lighting Score\n\n"
        "## Musical Features\n\n"
        "## Metadata\n"
        "- Song: Test Song\n"
        "- Artist: Test Artist\n"
        "- Duration: 0:50\n"
        "- BPM: 120.000\n"
        "- Time Signature: 4/4\n"
        "- Key: Am\n\n"
        "## Energy Profile\n"
        "- Loudness Mean: 0.500\n"
        "- Loudness Peak: 1.200\n"
        "- Loudness P90: 1.000\n"
        "- Dynamic Range: 1.200\n"
        "- Transient Density: 0.450\n"
        "- Energy Trend: wave\n"
        "- Brightness Trend: rising\n"
        "- Centroid Mean: 0.180\n"
        "- Centroid Peak: 0.310\n"
        "- Onset Count: 12\n"
        "- Onset Density/Minute: 14.400\n"
        "- Flux Mean: 0.420\n"
        "- Flux Peak: 1.800\n"
        "- Brightness Summary: Centroid stays balanced overall, peaks at 0.310, and trends rising.\n"
        "- Flux Summary: Onset flux is spiky with mean 0.420, peak 1.800, and 12 detected onset anchors.\n\n"
        "## Structure\n"
        "| Section | Time Range | Music |\n"
        "|---|---|---|\n"
        "| Intro | 1.36-35.82 | Intro stays restrained. |\n"
        "| Instrumental | 35.82-50.14 | Instrumental opens the groove. |\n\n"
        "## Structure Summary\n"
        "2 sections with an overall wave energy trend, rising brightness arc, and 12 detected onset anchors.\n\n"
        "## Mapping Rules\n"
        "- Bass -> dimmer pulses\n\n"
        "## Section Plan\n\n"
        "### Intro [1.36-35.82]\n\n"
        "Music: Intro stays restrained.\n"
        "Energy: Low energy with a hold contour, loudness peak 0.400, centroid mean 0.110.\n"
        "Energy Metrics: level low, trend hold, loudness peak 0.400, centroid mean 0.110, flux mean 0.210\n"
        "Visual Implications: Narrow the rig\n\n"
        "### Instrumental [35.82-50.14]\n\n"
        "Music: Instrumental opens the groove.\n"
        "Energy: High energy with a push contour, loudness peak 1.200, centroid mean 0.220.\n"
        "Energy Metrics: level high, trend push, loudness peak 1.200, centroid mean 0.220, flux mean 0.610\n"
        "Visual Implications: Use phrase-led motion\n"
    )


def test_main_option_7_calls_markdown_generation(tmp_path: Path, monkeypatch) -> None:
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    calls: list[Path] = []
    inputs = iter(["13", "16"])

    monkeypatch.setattr(analyze_song, "resolve_song", lambda song_arg: song_path)
    monkeypatch.setattr(analyze_song, "autodetect_device", lambda: "cpu")
    monkeypatch.setattr(analyze_song, "run_generate_md_for", lambda current_song: calls.append(current_song))
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(sys, "argv", ["analyze_song.py"])

    result = analyze_song.main()

    assert result == 0
    assert calls == [song_path]


def test_main_generate_md_flag_calls_markdown_generation(tmp_path: Path, monkeypatch) -> None:
    song_path = tmp_path / "songs" / "Flag Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    calls: list[Path] = []

    monkeypatch.setattr(analyze_song, "resolve_song", lambda song_arg: song_path)
    monkeypatch.setattr(analyze_song, "autodetect_device", lambda: "cpu")
    monkeypatch.setattr(analyze_song, "run_generate_md_for", lambda current_song: calls.append(current_song))
    monkeypatch.setattr(sys, "argv", ["analyze_song.py", "--song", "Flag Song.mp3", "--generate-md"])

    result = analyze_song.main()

    assert result == 0
    assert calls == [song_path]


def test_generate_md_keeps_duplicate_section_labels_distinct(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Title - Artist.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_meta_dir = meta_root / "Title - Artist"
    song_meta_dir.mkdir(parents=True)
    (song_meta_dir / "music_feature_layers.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "title": "Title - Artist",
                    "artist": "Artist",
                    "duration_s": 8.0,
                    "bpm": 120.0,
                    "time_signature": "4/4",
                    "key": "D major",
                },
                "energy_profile": {
                    "energy_trend": "wave",
                    "dynamic_range": 1.2,
                    "transient_density": 0.45,
                    "loudness_mean": 0.5,
                    "loudness_peak": 1.2,
                    "loudness_percentile_90": 1.0,
                    "onset_count": 12,
                    "onset_density_per_minute": 14.4,
                    "flux_mean": 0.42,
                    "flux_peak": 1.8,
                    "brightness_trend": "rising",
                    "centroid_mean": 0.18,
                    "centroid_peak": 0.31,
                    "centroid_summary": "Centroid stays balanced overall, peaks at 0.310, and trends rising.",
                    "flux_summary": "Onset flux is spiky with mean 0.420, peak 1.800, and 12 detected onset anchors.",
                },
                "timeline": {
                    "sections": [
                        {"name": "Instrumental", "start_s": 0.0, "end_s": 4.0},
                        {"name": "Instrumental", "start_s": 4.0, "end_s": 8.0},
                    ]
                },
                "structure_summary": "2 sections with an overall wave energy trend, rising brightness arc, and 12 detected onset anchors.",
                "mapping_rules": ["Bass -> dimmer pulses"],
                "section_cards": [
                    {
                        "section_id": "instrumental-0.00",
                        "section_name": "Instrumental",
                        "start_s": 0.0,
                        "end_s": 4.0,
                        "music_description": "First instrumental section.",
                        "energy_description": "Low energy with a hold contour, loudness peak 0.400, centroid mean 0.110.",
                        "energy_profile": {"level": "low", "trend": "hold", "loudness_peak": 0.4, "centroid_mean": 0.11, "flux_mean": 0.21},
                        "visual_implications": ["Narrow the rig"],
                    },
                    {
                        "section_id": "instrumental-4.00",
                        "section_name": "Instrumental",
                        "start_s": 4.0,
                        "end_s": 8.0,
                        "music_description": "Second instrumental section.",
                        "energy_description": "High energy with a push contour, loudness peak 1.200, centroid mean 0.220.",
                        "energy_profile": {"level": "high", "trend": "push", "loudness_peak": 1.2, "centroid_mean": 0.22, "flux_mean": 0.61},
                        "visual_implications": ["Use phrase-led motion"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    output_path = analyze_song.run_generate_md_for(song_path, meta_path=meta_root)
    rendered = output_path.read_text(encoding="utf-8")

    assert "| Instrumental | 0.00-4.00 | First instrumental section. |" in rendered
    assert "| Instrumental | 4.00-8.00 | Second instrumental section. |" in rendered