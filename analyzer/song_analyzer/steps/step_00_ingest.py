import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from ..io.audio_decode import decode_to_wav
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
    dest_wav = temp_dir / "audio" / "source.wav"
    try:
        info = decode_to_wav(song_path, dest_wav)
        timeline = {
            "schema_version": "1.0",
            "song_slug": slug,
            "duration_s": float(info["duration_s"]),
            "sample_rate_hz": int(info["sample_rate_hz"]),
            "channels": int(info["channels"]),
            "source_audio": {"original": str(song_path), "decoded_wav": str(dest_wav)}
        }
        timeline_path = out_dir / "analysis" / "timeline.json"
        stable_write_json(timeline_path, timeline)
        seconds = time.time() - start
        return StepResult(name="ingest", status="ok", artifacts=[str(timeline_path)], seconds=seconds)
    except Exception as exc:
        seconds = time.time() - start
        failure = FailureRecord(code="IO_ERROR", message=str(exc), detail=repr(exc), exception_type=type(exc).__name__, retryable=False)
        return StepResult(name="ingest", status="failed", artifacts=[], seconds=seconds, failure=failure)
