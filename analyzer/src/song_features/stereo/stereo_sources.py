from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np


ANALYZER_ROOT = Path(__file__).resolve().parents[3]
LOCAL_PATH_ALIASES = {
    Path("/app/songs"): ANALYZER_ROOT / "songs",
    Path("/app/meta"): ANALYZER_ROOT / "meta",
    Path("/app/analyzer/temp_files"): ANALYZER_ROOT / "temp_files",
}


def load_stereo_audio(audio_path: Path) -> tuple[np.ndarray | None, int | None, bool]:
    audio, sample_rate = librosa.load(str(audio_path), sr=None, mono=False)
    data = np.asarray(audio, dtype=np.float32)
    if data.ndim == 1:
        return None, sample_rate, False
    if data.ndim != 2:
        return None, sample_rate, False
    if data.shape[0] == 2:
        return data, sample_rate, True
    if data.shape[1] == 2:
        return data.T, sample_rate, True
    return None, sample_rate, False


def discover_audio_sources(song_path: Path, stems_dir: str | None) -> dict[str, Path]:
    sources = {"mix": song_path}
    if not stems_dir:
        return sources
    stems_root = resolve_audio_path(Path(stems_dir))
    for stem_name in ["drums", "bass", "vocals", "other"]:
        candidates = sorted(stems_root.glob(f"{stem_name}.*"))
        if candidates:
            sources[stem_name] = candidates[0]
    return sources


def resolve_audio_path(path: Path) -> Path:
    if path.exists():
        return path
    for source_root, local_root in LOCAL_PATH_ALIASES.items():
        try:
            relative = path.relative_to(source_root)
        except ValueError:
            continue
        candidate = local_root / relative
        if candidate.exists():
            return candidate
    return path