import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

import numpy as np

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
        import openl3
        import soundfile as sf
        wav_path = temp_dir / "audio" / "source.wav"
        audio, sr = sf.read(str(wav_path))
        # Use openl3 embeddings
        emb, ts = openl3.get_audio_embedding(audio, sr, hop_size=1.0, center=False)
        # self-similarity
        sim = np.dot(emb, emb.T)
        novelty = np.abs(np.diff(sim.mean(axis=0)))
        # peak-pick simple
        peaks = (novelty > np.mean(novelty) + np.std(novelty)).nonzero()[0]
        sections = []
        last = 0.0
        for p in peaks:
            t = float(p * 1.0)
            sections.append({"start_s": last, "end_s": t, "label": "section", "confidence": 0.5})
            last = t
        sections.append({"start_s": last, "end_s": float(len(audio)/sr), "label": "section", "confidence": 0.5})
        path = out_dir / "analysis" / "sections.json"
        stable_write_json(path, {"schema_version": "1.0", "source": {"name": "openl3"}, "sections": sections})
        seconds = time.time() - start
        return StepResult(name="sections", status="ok", artifacts=[str(path)], seconds=seconds)
    except Exception as exc:
        seconds = time.time() - start
        failure = FailureRecord(code="MODEL_ERROR", message=str(exc), detail=repr(exc), exception_type=type(exc).__name__, retryable=False)
        return StepResult(name="sections", status="failed", artifacts=[], seconds=seconds, failure=failure)
