import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "analyzer" / "beat_comparison.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("beat_comparison_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_source_formats(tmp_path):
    mod = _load_module()

    essentia_file = tmp_path / "rhythm.json"
    essentia_file.write_text(json.dumps({"rhythm": {"beats": [0.3, "bad", 0.1]}}), encoding="utf-8")
    beats, skipped = mod._load_essentia_beats(essentia_file)
    assert beats == [0.1, 0.3]
    assert skipped == 1

    moises_file = tmp_path / "moises.json"
    moises_file.write_text(
        json.dumps([{"time": 1.2}, {"beatNum": 2}, {"time": "x"}, {"time": 1.0}]),
        encoding="utf-8",
    )
    beats, skipped = mod._load_moises_beats(moises_file)
    assert beats == [1.0, 1.2]
    assert skipped == 2

    analyzer_file = tmp_path / "beats.json"
    analyzer_file.write_text(json.dumps({"beats": [2.2, "oops", 2.0]}), encoding="utf-8")
    beats, skipped = mod._load_analyzer_beats(analyzer_file)
    assert beats == [2.0, 2.2]
    assert skipped == 1


def test_threshold_boundary_is_close_true():
    mod = _load_module()
    stats = mod._window_error_stats([0.0], [0.06])
    assert stats["median_error_ms"] == 60.0
    assert stats["close"] is True


def test_consensus_ranking_and_report_file(tmp_path):
    mod = _load_module()

    song_file = tmp_path / "songs" / "Test Song.mp3"
    song_file.parent.mkdir(parents=True)
    song_file.write_bytes(b"stub")

    song_meta_dir = tmp_path / "meta" / "Test Song"
    (song_meta_dir / "essentia").mkdir(parents=True)
    (song_meta_dir / "moises").mkdir(parents=True)

    essentia_beats = [0.0451092719, 0.5626637556, 0.9906123968, 1.3359297445, 2.1030415688, 2.6507081483]
    moises_beats = [0.1693524064, 0.6369840893, 1.1592692485, 1.6692329759, 2.01623997, 2.4565184201]
    analyzer_beats = [0.0821133599, 0.4102536485, 1.1246514834, 1.6397943861, 2.1580155870, 2.5359204734]

    (song_meta_dir / "essentia" / "rhythm.json").write_text(
        json.dumps({"rhythm": {"beats": essentia_beats}}), encoding="utf-8"
    )
    (song_meta_dir / "moises" / "beats.json").write_text(
        json.dumps([{"time": t, "beatNum": 1} for t in moises_beats]), encoding="utf-8"
    )
    (song_meta_dir / "beats.json").write_text(json.dumps({"beats": analyzer_beats}), encoding="utf-8")

    report = mod.run_compare_beat_times_for(song_file, meta_path=tmp_path / "meta")

    assert report is not None
    assert report["overall"]["winner"] == "analyzer"
    assert report["windows"]

    output_file = song_meta_dir / "beat_comparison.json"
    assert output_file.exists()
    loaded = json.loads(output_file.read_text(encoding="utf-8"))
    assert loaded["config"]["close_threshold_ms"] == 60.0
    assert loaded["overall"]["winner"] == "analyzer"
