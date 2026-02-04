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
    drums_wav = temp_dir / "stems" / "drums.wav"
    try:
        # Attempt to import omnizart drum transcription
        try:
            from omnizart.inference import MusicTranscription
            mt = MusicTranscription(device=cfg.device)
            events = mt.transcribe(str(drums_wav))
            # Convert to simple events (best-effort)
            evs = []
            for e in events:
                evs.append({"time_s": float(e.time), "label": getattr(e, 'label', 'unknown'), "confidence": 1.0})
        except Exception as exc:
            raise
        path = out_dir / "analysis" / "onsets.json"
        stable_write_json(path, {"schema_version": "1.0", "source": {"name": "omnizart"}, "events": evs})
        seconds = time.time() - start
        return StepResult(name="drums", status="ok", artifacts=[str(path)], seconds=seconds)
    except Exception as exc:
        seconds = time.time() - start
        failure = FailureRecord(code="MODEL_ERROR", message=str(exc), detail=repr(exc), exception_type=type(exc).__name__, retryable=False)
        return StepResult(name="drums", status="failed", artifacts=[], seconds=seconds, failure=failure)
