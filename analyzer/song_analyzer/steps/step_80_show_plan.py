import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from ..io.json_write import stable_write_json
from ..models.failures import FailureRecord


@dataclass
class StepResult:
    name: str
    status: str
    artifacts: list
    seconds: float = 0.0
    failure: Optional[FailureRecord] = None


def run(song_path: Path, out_dir: Path, temp_dir: Path, cfg):
    start = time.time()
    try:
        includes = {
            "timeline": "../analysis/timeline.json",
            "stems": "../analysis/stems.json",
            "beats": "../analysis/beats.json",
            "energy": "../analysis/energy.json",
            "onsets": "../analysis/onsets.json",
            "vocals": "../analysis/vocals.json",
            "sections": "../analysis/sections.json",
            "roles": "./roles.json",
            "patterns": "./patterns.json",
            "moments": "./moments.json"
        }
        show_plan = {"includes": includes, "meta": {"style": "auto", "llm_version": "unknown", "confidence": 0.0}}
        path = out_dir / "show_plan" / "show_plan.json"
        stable_write_json(path, show_plan)
        # roles and moments placeholders
        roles = {"schema_version": "1.0", "roles": {"groove": {"primary": "drums", "features": ["beats", "kick", "snare"]}}}
        moments = {"schema_version": "1.0", "moments": []}
        stable_write_json(out_dir / "show_plan" / "roles.json", roles)
        stable_write_json(out_dir / "show_plan" / "moments.json", moments)
        seconds = time.time() - start
        return StepResult(name="show_plan", status="ok", artifacts=[str(path)], seconds=seconds)
    except Exception as exc:
        seconds = time.time() - start
        failure = FailureRecord(code="UNKNOWN", message=str(exc), detail=repr(exc), exception_type=type(exc).__name__, retryable=False)
        return StepResult(name="show_plan", status="failed", artifacts=[], seconds=seconds, failure=failure)
