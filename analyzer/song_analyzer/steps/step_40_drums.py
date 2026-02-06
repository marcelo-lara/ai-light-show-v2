"""Step 40: Drums - Extract drum events (kick/snare/hihat)."""

from pathlib import Path
import numpy as np

from ..config import AnalysisContext
from ..io.json_write import write_json
from ..models.schemas import StepResult, OnsetsArtifact


def run(ctx: AnalysisContext) -> StepResult:
    """Run the drums step."""

    # Check if stems exist
    stems_json = ctx.analysis_dir / "stems.json"
    if not stems_json.exists():
        return StepResult(
            failure={
                "code": "DEPENDENCY_ERROR",
                "message": f"Stems analysis not found: {stems_json}",
                "retryable": False
            }
        )

    # Load stems info
    import json
    with open(stems_json) as f:
        stems_data = json.load(f)

    # Get drums stem
    drums_path = stems_data["stems"].get("drums")
    if not drums_path or not Path(drums_path).exists():
        return StepResult(
            failure={
                "code": "DEPENDENCY_ERROR",
                "message": f"Drums stem not found: {drums_path}",
                "retryable": False
            }
        )

    # Extract drum events
    events = extract_drum_events(drums_path)

    # Create artifact
    onsets_artifact = OnsetsArtifact(
        schema_version="1.0",
        source={
            "name": "librosa",
            "model": "onset_strength",
            "device": ctx.config.device
        },
        events=events
    )

    # Write onsets.json
    onsets_path = ctx.analysis_dir / "onsets.json"
    write_json(onsets_artifact.dict(), onsets_path, ctx.config.json_precision)

    return StepResult(artifacts_written=[onsets_path])


def extract_drum_events(audio_path: str) -> list[dict]:
    """Extract drum events from audio using onset strength."""

    import librosa

    # Load audio
    y, sr = librosa.load(audio_path, sr=None)

    # Compute onset strength
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    # Detect onsets
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)

    # Convert to times
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # Classify drum types (simplified heuristic)
    events = []
    for time_s in onset_times:
        # Simple classification based on spectral content around the onset
        # This is a placeholder - a real implementation would use ML classification
        label = classify_drum_hit(y, sr, time_s)
        events.append({
            "time_s": round(float(time_s), 3),
            "label": label,
            "confidence": 0.7  # Placeholder confidence
        })

    return events


def classify_drum_hit(y: np.ndarray, sr: int, time_s: float) -> str:
    """Simple heuristic classification of drum hits."""

    import librosa

    # Extract a short window around the hit
    start_sample = max(0, int((time_s - 0.01) * sr))
    end_sample = min(len(y), int((time_s + 0.05) * sr))
    window = y[start_sample:end_sample]

    if len(window) == 0:
        return "unknown"

    # Simple heuristics based on spectral centroid and RMS
    centroid = librosa.feature.spectral_centroid(y=window, sr=sr)[0].mean()

    # Rough classification thresholds
    if centroid < 1000:
        return "kick"  # Low frequency
    elif centroid < 3000:
        return "snare"  # Mid frequency
    else:
        return "hihat"  # High frequency