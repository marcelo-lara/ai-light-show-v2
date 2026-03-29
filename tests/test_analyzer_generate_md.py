import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analyzer"))

import analyze_song


def test_run_generate_md_for_writes_song_markdown(tmp_path: Path):
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_meta_dir = meta_root / "Test Song"
    song_meta_dir.mkdir(parents=True)
    (song_meta_dir / "sections.json").write_text(
        json.dumps([
            {"start": 1.36, "end": 35.82, "label": "Intro"},
            {"start_s": 35.82, "end_s": 50.14, "name": "Instrumental"},
        ]),
        encoding="utf-8",
    )

    output_path = analyze_song.run_generate_md_for(song_path, meta_path=meta_root)

    assert output_path == song_meta_dir / "Test Song.md"
    assert output_path.read_text(encoding="utf-8") == (
        "# Test Song - Light Show\n\n"
        "## Intro [1.36-35.82]\n\n"
        "## Instrumental [35.82-50.14]\n"
    )


def test_main_option_6_calls_markdown_generation(tmp_path: Path, monkeypatch):
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    calls: list[Path] = []
    inputs = iter(["6", "9"])

    monkeypatch.setattr(analyze_song, "resolve_song", lambda song_arg: song_path)
    monkeypatch.setattr(analyze_song, "autodetect_device", lambda: "cpu")
    monkeypatch.setattr(analyze_song, "run_generate_md_for", lambda current_song: calls.append(current_song))
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(sys, "argv", ["analyze_song.py"])

    result = analyze_song.main()

    assert result == 0
    assert calls == [song_path]


def test_main_generate_md_flag_calls_markdown_generation(tmp_path: Path, monkeypatch):
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