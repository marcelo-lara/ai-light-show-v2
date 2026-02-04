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
    source_wav = temp_dir / "audio" / "source.wav"
    try:
        # librosa beat tracking (CPU-friendly, robust)
        import librosa
        import soundfile as sf
        import numpy as np
        y, sr = sf.read(str(source_wav))
        # librosa expects mono audio for beat tracking
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        # onset envelope
        oenv = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, beat_frames = librosa.beat.beat_track(onset_envelope=oenv, sr=sr)
        beats_times = librosa.frames_to_time(beat_frames, sr=sr)
        beats_list = [float(b) for b in beats_times]
        tempo_segment = {"start_s": 0.0, "end_s": float(len(y)/sr), "bpm": float(tempo), "confidence": 1.0}

        # Attempt a more robust downbeat estimation using madmom if it's available; otherwise fall back to heuristic (every 4th beat)
        downbeats = []
        downbeat_method = "heuristic"
        try:
            # madmom's downbeat model (optional)
            from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor
            proc = RNNDownBeatProcessor()(str(source_wav))
            dbn = DBNDownBeatTrackingProcessor()(proc)
            # dbn returns time positions; filter to beat times
            downbeats = [float(t) for t in dbn]
            downbeat_method = "madmom"
        except Exception:
            # Fallback heuristic (assume 4/4): every 4th beat is a downbeat
            if len(beats_list) >= 4:
                downbeats = [beats_list[i] for i in range(0, len(beats_list), 4)]
            else:
                downbeats = []
            downbeat_method = "heuristic"

        beats_json = {
            "schema_version": "1.0",
            "source": {"primary": {"name": "librosa", "model": "beat_track", "device": cfg.device}, "downbeat": {"method": downbeat_method}},
            "beats": beats_list,
            "downbeats": downbeats,
            "tempo": {"unit": "bpm", "segments": [tempo_segment]}
        }
        path = out_dir / "analysis" / "beats.json"
        stable_write_json(path, beats_json)
        seconds = time.time() - start
        return StepResult(name="beats", status="ok", artifacts=[str(path)], seconds=seconds)
    except Exception as exc:
        seconds = time.time() - start
        failure = FailureRecord(code="MODEL_ERROR", message=str(exc), detail=repr(exc), exception_type=type(exc).__name__, retryable=False)
        return StepResult(name="beats", status="failed", artifacts=[], seconds=seconds, failure=failure)
