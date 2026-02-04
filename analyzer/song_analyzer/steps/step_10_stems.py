"""Step 10: Stems - Separate audio into stems using Demucs."""

import time
from pathlib import Path

from ..config import AnalysisContext
from ..io.json_write import write_json
from ..ml.demucs import DemucsSeparator
from ..models.schemas import StepResult, StemsArtifact


def run(ctx: AnalysisContext) -> StepResult:
    """Run the stems separation step."""

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

    # Create stems directory
    stems_dir = ctx.temp_dir / "stems"
    stems_dir.mkdir(exist_ok=True)

    # Initialize separator
    try:
        separator = DemucsSeparator(
            model_name=ctx.config.stems_model,
            device=ctx.config.device
        )
    except Exception as e:
        return StepResult(
            failure={
                "code": "MODEL_ERROR",
                "message": f"Failed to initialize Demucs model: {str(e)}",
                "exception_type": type(e).__name__,
                "retryable": True
            }
        )

    # Separate stems
    try:
        result = separator.separate(source_wav, stems_dir)
    except Exception as e:
        return StepResult(
            failure={
                "code": "MODEL_ERROR",
                "message": f"Stem separation failed: {str(e)}",
                "exception_type": type(e).__name__,
                "retryable": True
            }
        )

    # Create artifact
    stems_artifact = StemsArtifact(
        schema_version="1.0",
        status="ok",
        model=result["model"],
        stems=result["stems"]
    )

    # Write stems.json
    stems_path = ctx.analysis_dir / "stems.json"
    write_json(stems_artifact.dict(), stems_path, ctx.config.json_precision)

    artifacts = [stems_path]
    artifacts.extend([Path(p) for p in result["stems"].values()])

    return StepResult(artifacts_written=artifacts)