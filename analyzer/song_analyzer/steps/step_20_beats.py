"""Step 20: Beats - Beat grid + tempo curve."""

from pathlib import Path

from ..config import AnalysisContext
from ..io.json_write import write_json
from ..ml.beat_tracker import BeatTracker
from ..models.schemas import StepResult, BeatsArtifact


def run(ctx: AnalysisContext) -> StepResult:
    """Run the beats step."""

    # Check if source audio exists
    source_wav = ctx.temp_dir / "audio" / "source.wav"
    if not source_wav.exists():
        return StepResult(
            failure={
                "code": "DEPENDENCY_ERROR",
                "message": f"Source audio not found: {source_wav}",
                "retryable": False
            }
        )

    # Initialize beat tracker
    try:
        tracker = BeatTracker(device=ctx.config.device)
    except Exception as e:
        return StepResult(
            failure={
                "code": "MODEL_ERROR",
                "message": f"Failed to initialize beat tracker: {str(e)}",
                "exception_type": type(e).__name__,
                "retryable": True
            }
        )

    # Track beats
    try:
        result = tracker.track_beats(source_wav)
    except Exception as e:
        return StepResult(
            failure={
                "code": "MODEL_ERROR",
                "message": f"Beat tracking failed: {str(e)}",
                "exception_type": type(e).__name__,
                "retryable": True
            }
        )

    # Create artifact
    beats_artifact = BeatsArtifact(
        schema_version="1.0",
        source=result["source"],
        beats=result["beats"],
        downbeats=result["downbeats"],
        tempo=result["tempo"]
    )

    # Write beats.json
    beats_path = ctx.analysis_dir / "beats.json"
    write_json(beats_artifact.dict(), beats_path, ctx.config.json_precision)

    return StepResult(artifacts_written=[beats_path])