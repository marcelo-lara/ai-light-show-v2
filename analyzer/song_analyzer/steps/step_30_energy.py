"""Step 30: Energy - Compute energy curves per stem."""

from pathlib import Path
import numpy as np

from ..config import AnalysisContext
from ..io.json_write import write_json
from ..models.schemas import StepResult, EnergyArtifact


def run(ctx: AnalysisContext) -> StepResult:
    """Run the energy step."""

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

    # Compute energy for each stem
    fps = 10  # 10 Hz sampling rate for energy curves
    energy_tracks = {}

    # Process each stem
    for stem_name, stem_path in stems_data["stems"].items():
        stem_file = Path(stem_path)
        if stem_file.exists():
            times_s, values = compute_energy_curve(str(stem_file), fps)
            energy_tracks[stem_name] = {
                "times_s": times_s,
                "values": values
            }
        else:
            # Use zeros if stem file missing
            energy_tracks[stem_name] = {
                "times_s": [],
                "values": []
            }

    # Create artifact
    energy_artifact = EnergyArtifact(
        schema_version="1.0",
        fps=fps,
        unit="rms",
        tracks=energy_tracks
    )

    # Write energy.json
    energy_path = ctx.analysis_dir / "energy.json"
    write_json(energy_artifact.dict(), energy_path, ctx.config.json_precision)

    return StepResult(artifacts_written=[energy_path])


def compute_energy_curve(audio_path: str, fps: int) -> tuple[list[float], list[float]]:
    """Compute RMS energy curve for audio file."""

    import librosa

    # Load audio
    y, sr = librosa.load(audio_path, sr=None)

    # Compute RMS energy with hop length for desired FPS
    hop_length = int(sr / fps)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    # Create time array
    times_s = librosa.times_like(rms, sr=sr, hop_length=hop_length)

    return times_s.tolist(), rms.tolist()