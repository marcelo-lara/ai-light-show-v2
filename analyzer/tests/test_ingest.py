import subprocess
import sys
from pathlib import Path
import numpy as np
import soundfile as sf

# Ensure analyzer package on sys.path for test discovery when running from repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYZER_PKG = REPO_ROOT / 'analyzer'
if str(ANALYZER_PKG) not in sys.path:
    sys.path.insert(0, str(ANALYZER_PKG))

from song_analyzer.pipeline import run_pipeline, AnalysisConfig


def ensure_sample_song(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    # generate 3s sine and write wav then convert to mp3 via ffmpeg
    sr = 44100
    t = np.linspace(0, 3, int(sr*3), endpoint=False)
    x = 0.1 * np.sin(2 * np.pi * 440 * t)
    wav = path.with_suffix('.wav')
    sf.write(str(wav), x, sr)
    cmd = ['ffmpeg', '-y', '-i', str(wav), str(path)]
    subprocess.check_call(cmd)


def test_ingest_creates_timeline(tmp_path):
    workdir = Path(__file__).resolve().parents[1]
    song = workdir / 'songs' / 'sono - keep control.mp3'
    ensure_sample_song(song)
    out_dir = tmp_path / 'metadata'
    temp_dir = tmp_path / 'temp_files'
    cfg = AnalysisConfig(out_dir=out_dir, temp_dir=temp_dir, device='cpu', stems_model='demucs:htdemucs_ft', overwrite=True, workdir=workdir)
    run_pipeline(song, cfg, until='ingest')
    # pipeline uses normalized slug for output directory names
    from song_analyzer.io.paths import make_slug
    slug = make_slug(song.name)
    timeline_path = out_dir / slug / 'analysis' / 'timeline.json'
    assert timeline_path.exists(), f"Missing timeline at {timeline_path}"
    j = timeline_path.read_text()
    assert 'duration_s' in j
