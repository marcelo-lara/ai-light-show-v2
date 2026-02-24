from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np


def _tempo_to_float(tempo: float | np.ndarray) -> float:
    if isinstance(tempo, np.ndarray):
        if tempo.size == 0:
            return 0.0
        return float(tempo.reshape(-1)[0])
    return float(tempo)


def find_beats_and_downbeats(song_path: str | Path) -> dict:
    """Find beats and downbeats using librosa only.

    Downbeats are inferred by selecting the most accented beat in a 4-beat cycle.
    """
    song_path = Path(song_path).expanduser().resolve()
    if not song_path.exists():
        raise FileNotFoundError(f"Song file not found: {song_path}")

    y, sr = librosa.load(str(song_path), sr=None, mono=True)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, units="frames")

    beat_frames = np.asarray(beat_frames, dtype=int)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    if beat_frames.size >= 4:
        best_offset = 0
        best_score = float("-inf")
        for offset in range(4):
            candidate = beat_frames[offset::4]
            if candidate.size == 0:
                continue
            score = float(np.sum(onset_env[candidate]))
            if score > best_score:
                best_score = score
                best_offset = offset
        downbeat_frames = beat_frames[best_offset::4]
    elif beat_frames.size > 0:
        downbeat_frames = beat_frames[:1]
    else:
        downbeat_frames = np.array([], dtype=int)

    downbeat_times = librosa.frames_to_time(downbeat_frames, sr=sr).tolist()

    beat_strength = float(np.mean(onset_env[beat_frames])) if beat_frames.size else 0.0
    downbeat_strength = (
        float(np.mean(onset_env[downbeat_frames])) if downbeat_frames.size else 0.0
    )

    return {
        "method": "librosa",
        "tempo_bpm": _tempo_to_float(tempo),
        "sample_rate": int(sr),
        "beats": [float(t) for t in beat_times],
        "downbeats": [float(t) for t in downbeat_times],
        "beat_count": int(beat_frames.size),
        "downbeat_count": int(downbeat_frames.size),
        "beat_strength_mean": beat_strength,
        "downbeat_strength_mean": downbeat_strength,
        "meter_assumption": "4/4",
    }
