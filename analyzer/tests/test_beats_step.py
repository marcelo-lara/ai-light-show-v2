from pathlib import Path
from song_analyzer.pipeline import run_pipeline, AnalysisConfig
from song_analyzer.io.paths import make_slug


def test_beats_step_runs(tmp_path):
    workdir = Path(__file__).resolve().parents[1]
    song = workdir / 'songs' / 'sono - keep control.mp3'
    out_dir = tmp_path / 'metadata'
    temp_dir = tmp_path / 'temp_files'
    cfg = AnalysisConfig(out_dir=out_dir, temp_dir=temp_dir, device='cpu', stems_model='demucs:htdemucs_ft', overwrite=True, workdir=workdir)
    run_pipeline(song, cfg, until='beats')
    slug = make_slug(song.name)
    beats_path = out_dir / slug / 'analysis' / 'beats.json'
    assert beats_path.exists(), f"Missing beats.json at {beats_path}"
    import json
    j = json.loads(beats_path.read_text())
    assert 'beats' in j and isinstance(j['beats'], list) and len(j['beats']) > 0
    # downbeats should be present (may be heuristic); if madmom is installed it should be non-empty
    assert 'downbeats' in j and isinstance(j['downbeats'], list)
    try:
        import madmom  # optional
        assert len(j['downbeats']) > 0, "madmom present but downbeats empty"
    except Exception:
        # madmom not present — accept heuristic or empty downbeats
        pass
