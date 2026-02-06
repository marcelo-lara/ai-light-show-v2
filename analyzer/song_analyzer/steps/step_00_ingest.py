"""Step 00: Ingest - Decode MP3 and extract basic metadata."""

import time
from pathlib import Path

from ..config import AnalysisContext
from ..io.audio_decode import decode_mp3_to_wav
from ..io.json_write import write_json
from ..models.schemas import StepResult, TimelineArtifact


def run(ctx: AnalysisContext) -> StepResult:
    """Run the ingest step."""

    # Decode MP3 to WAV
    source_wav = ctx.temp_dir / "audio" / "source.wav"
    try:
        metadata = decode_mp3_to_wav(ctx.song_path, source_wav)
    except Exception as e:
        return StepResult(
            failure={
                "code": "IO_ERROR",
                "message": f"Failed to decode MP3: {str(e)}",
                "exception_type": type(e).__name__,
                "retryable": True
            }
        )

    # Create timeline artifact
    timeline = TimelineArtifact(
        schema_version="1.0",
        song_slug=ctx.song_slug,
        duration_s=metadata["duration_s"],
        sample_rate_hz=metadata["sample_rate_hz"],
        channels=metadata["channels"],
        source_audio={
            "original": str(ctx.song_path),
            "decoded_wav": str(source_wav)
        }
    )

    # Write timeline.json
    timeline_path = ctx.analysis_dir / "timeline.json"
    write_json(timeline.dict(), timeline_path, ctx.config.json_precision)

    # Write run.json placeholder (will be updated by pipeline)
    run_path = ctx.analysis_dir / "run.json"
    run_data = {
        "schema_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "song": {
            "filename": ctx.song_path.name,
            "song_slug": ctx.song_slug,
            "sha256": "placeholder"  # Will be computed by pipeline
        },
        "environment": {},
        "steps": []
    }
    write_json(run_data, run_path, ctx.config.json_precision)

    return StepResult(
        artifacts_written=[timeline_path, run_path]
    )