import json
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

from .io.paths import make_slug, ensure_dirs
from .io.json_write import stable_write_json
from .models.schemas import RunSchema, StepRecord
from .models.failures import FailureRecord

logger = logging.getLogger(__name__)


@dataclass
class AnalysisConfig:
    out_dir: Path
    temp_dir: Path
    device: str = "auto"
    stems_model: str = "demucs:htdemucs_ft"
    overwrite: bool = False
    workdir: Path = Path('.')


class StepResult:
    def __init__(self, name: str, status: str = "ok", artifacts: Optional[List[str]] = None, seconds: float = 0.0, failure: Optional[FailureRecord] = None):
        self.name = name
        self.status = status
        self.artifacts = artifacts or []
        self.seconds = seconds
        self.failure = failure


def run_pipeline(song_path: Path, cfg: AnalysisConfig, until: Optional[str] = None):
    song_path = Path(song_path)
    if not song_path.exists():
        raise FileNotFoundError(song_path)

    slug = make_slug(song_path.name)
    out = cfg.out_dir / slug
    temp = cfg.temp_dir / slug
    ensure_dirs(out / "analysis")
    ensure_dirs(out / "show_plan")
    ensure_dirs(temp)

    run_schema = RunSchema.construct(song={'filename': song_path.name, 'song_slug': slug, 'sha256': None}, environment={}, steps=[])
    run_path = out / "analysis" / "run.json"

    # Sequentially run steps; for now import step modules lazily
    steps_to_run = [
        ("ingest", "song_analyzer.steps.step_00_ingest"),
        ("stems", "song_analyzer.steps.step_10_stems"),
        ("beats", "song_analyzer.steps.step_20_beats"),
        ("energy", "song_analyzer.steps.step_30_energy"),
        ("drums", "song_analyzer.steps.step_40_drums"),
        ("vocals", "song_analyzer.steps.step_50_vocals"),
        ("sections", "song_analyzer.steps.step_60_sections"),
        ("patterns", "song_analyzer.steps.step_70_patterns"),
        ("show_plan", "song_analyzer.steps.step_80_show_plan"),
    ]

    for name, module_path in steps_to_run:
        if until and name != until and until in [s for s, _ in steps_to_run]:
            # run until inclusive
            pass
        start = time.time()
        try:
            mod = __import__(module_path, fromlist=["*"])
            result = mod.run(song_path=song_path, out_dir=out, temp_dir=temp, cfg=cfg)
            seconds = time.time() - start
            failure_field = result.failure.dict() if getattr(result, 'failure', None) is not None else None
            rec = StepRecord(name=name, status=result.status, artifacts=result.artifacts, seconds=seconds, failure=failure_field)
        except Exception as exc:  # capture failure as per design
            seconds = time.time() - start
            failure = FailureRecord(code="UNKNOWN", message=str(exc), detail=repr(exc), exception_type=type(exc).__name__, retryable=False)
            rec = StepRecord(name=name, status="failed", artifacts=[], seconds=seconds, failure=failure.dict())
            logger.exception("Step %s failed", name)
        run_schema.steps.append(rec)
        stable_write_json(run_path, run_schema.dict())
        if until and name == until:
            break

    print(f"Run complete; see {run_path}")
