import time
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from ..io.paths import make_slug
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
    slug = make_slug(song_path.name)
    source_wav = temp_dir / "audio" / "source.wav"
    stems_dir = temp_dir / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    model_spec = cfg.stems_model.split(":", 1)[-1]
    try:
        # Try to call demucs CLI; if not installed, this will raise
        cmd = ["demucs", "-n", model_spec, "-o", str(temp_dir), str(source_wav)]
        subprocess.check_call(cmd)
        demucs_exit_error = None
    except FileNotFoundError as exc:
        seconds = time.time() - start
        failure = FailureRecord(code="DEPENDENCY_ERROR", message="demucs CLI not found", detail=str(exc), exception_type=type(exc).__name__, retryable=False)
        return StepResult(name="stems", status="failed", artifacts=[], seconds=seconds, failure=failure)
    except subprocess.CalledProcessError as exc:
        # demucs returned non-zero; continue to check for output files
        demucs_exit_error = exc

    # demucs may write stems even if its process exit code was non-zero (e.g., missing optional codec).
    # Check for expected stem files and consider the step successful if they exist.
    stems = {
        "drums": str(stems_dir / "drums.wav"),
        "bass": str(stems_dir / "bass.wav"),
        "vocals": str(stems_dir / "vocals.wav"),
        "other": str(stems_dir / "other.wav"),
    }
    existing = [p for p in stems.values() if (Path(p).exists())]
    if existing:
        stems_json = {
            "schema_version": "1.0",
            "status": "ok" if demucs_exit_error is None else "ok_with_warnings",
            "model": {"name": "demucs", "variant": model_spec, "device": cfg.device},
            "stems": stems,
            "warnings": (None if demucs_exit_error is None else [str(demucs_exit_error)])
        }
        path = out_dir / "analysis" / "stems.json"
        stable_write_json(path, stems_json)
        seconds = time.time() - start
        return StepResult(name="stems", status="ok", artifacts=[str(path)], seconds=seconds)
    else:
        # No stems produced; if demucs had an exception capture details into FailureRecord
        seconds = time.time() - start
        if demucs_exit_error is not None:
            failure = FailureRecord(code="MODEL_ERROR", message="demucs failed", detail=repr(demucs_exit_error), exception_type=type(demucs_exit_error).__name__, retryable=False)
        else:
            failure = FailureRecord(code="UNKNOWN", message="demucs produced no stems", detail=None, exception_type=None, retryable=False)
        return StepResult(name="stems", status="failed", artifacts=[], seconds=seconds, failure=failure)
