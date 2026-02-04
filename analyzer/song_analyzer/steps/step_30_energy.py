import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import numpy as np
import soundfile as sf

from ..io.json_write import stable_write_json
from ..models.failures import FailureRecord


@dataclass
class StepResult:
    name: str
    status: str
    artifacts: list
    seconds: float = 0.0
    failure: Optional[FailureRecord] = None


def _rms(signal):
    return np.sqrt(np.mean(signal**2))


def run(song_path: Path, out_dir: Path, temp_dir: Path, cfg):
    start = time.time()
    try:
        mix_wav = temp_dir / "audio" / "source.wav"
        data, sr = sf.read(str(mix_wav))
        # Compute 10Hz RMS
        fps = 10
        window = int(sr / fps)
        times = []
        values = []
        for i in range(0, len(data), window):
            frame = data[i:i+window]
            if frame.ndim > 1:
                frame = np.mean(frame, axis=1)
            values.append(float(_rms(frame)))
            times.append(float(i / sr))
        energy_json = {"schema_version": "1.0", "fps": fps, "unit": "rms", "tracks": {"mix": {"times_s": times, "values": values}}}
        path = out_dir / "analysis" / "energy.json"
        stable_write_json(path, energy_json)
        seconds = time.time() - start
        return StepResult(name="energy", status="ok", artifacts=[str(path)], seconds=seconds)
    except Exception as exc:
        seconds = time.time() - start
        failure = FailureRecord(code="MODEL_ERROR", message=str(exc), detail=repr(exc), exception_type=type(exc).__name__, retryable=False)
        return StepResult(name="energy", status="failed", artifacts=[], seconds=seconds, failure=failure)
