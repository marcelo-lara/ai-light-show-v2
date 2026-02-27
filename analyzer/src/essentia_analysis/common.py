from __future__ import annotations

from pathlib import Path
from typing import Any

import essentia.standard as es
import numpy as np


def warn(message: str) -> None:
    print(f"WARNING: {message}")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, (np.floating, np.integer)):
        item = value.item()
        if isinstance(item, float):
            return round(item, 3)
        return item
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    return value


def is_stem_worth_analyzing(audio_path: str, min_duration: float = 15.0, silence_threshold: float = -60.0, min_active_ratio: float = 0.1) -> bool:
    """Check if a stem audio file is worth analyzing based on duration and activity."""
    try:
        loader = es.AudioLoader(filename=audio_path)
        audio, sr, *_ = loader()
        duration = len(audio) / sr

        if duration < min_duration:
            return False

        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        # Compute RMS energy in frames
        frame_size = 1024
        hop_size = 512
        rms = es.RMS()
        energies = []
        for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
            energies.append(rms(frame))

        if not energies:
            return False

        # Convert to dB
        energies_db = [20 * np.log10(e) if e > 0 else silence_threshold for e in energies]

        # Count active frames
        active_frames = sum(1 for e in energies_db if e > silence_threshold)
        active_ratio = active_frames / len(energies_db)

        return active_ratio >= min_active_ratio
    except Exception:
        return False
