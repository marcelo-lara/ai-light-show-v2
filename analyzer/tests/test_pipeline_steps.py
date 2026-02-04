import sys
from pathlib import Path
# Ensure analyzer package on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYZER_PKG = REPO_ROOT / 'analyzer'
if str(ANALYZER_PKG) not in sys.path:
    sys.path.insert(0, str(ANALYZER_PKG))

from song_analyzer.pipeline import run_pipeline, AnalysisConfig
from song_analyzer.io.paths import make_slug

def test_run_each_step(tmp_path):
    workdir = Path(__file__).resolve().parents[1]
    song = workdir / 'songs' / 'sono - keep control.mp3'
    out_dir = tmp_path / 'metadata'
    temp_dir = tmp_path / 'temp_files'
    cfg = AnalysisConfig(out_dir=out_dir, temp_dir=temp_dir, device='cpu', stems_model='demucs:htdemucs_ft', overwrite=True, workdir=workdir)
    steps = ['ingest','stems','beats','energy','drums','vocals','sections','patterns','show_plan']
    for s in steps:
        run_pipeline(song, cfg, until=s)
        slug = make_slug(song.name)
        run_json = out_dir / slug / 'analysis' / 'run.json'
        assert run_json.exists()
        j = run_json.read_text()
        assert s in j
