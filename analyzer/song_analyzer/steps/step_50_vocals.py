import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

import torch

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
    vocals_wav = temp_dir / "stems" / "vocals.wav"
    try:
        # Load Silero VAD via torch.hub
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False)
        torch.set_grad_enabled(False)
        get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks = utils
        wav = read_audio(str(vocals_wav))
        speech_timestamps = get_speech_timestamps(wav, model)
        segments = []
        for s in speech_timestamps:
            segments.append({"start_s": float(s['start']/16000.0), "end_s": float(s['end']/16000.0), "confidence": 1.0})
        path = out_dir / "analysis" / "vocals.json"
        stable_write_json(path, {"schema_version": "1.0", "source": {"name": "silero_vad"}, "segments": segments})
        seconds = time.time() - start
        return StepResult(name="vocals", status="ok", artifacts=[str(path)], seconds=seconds)
    except Exception as exc:
        seconds = time.time() - start
        failure = FailureRecord(code="MODEL_ERROR", message=str(exc), detail=repr(exc), exception_type=type(exc).__name__, retryable=False)
        return StepResult(name="vocals", status="failed", artifacts=[], seconds=seconds, failure=failure)
