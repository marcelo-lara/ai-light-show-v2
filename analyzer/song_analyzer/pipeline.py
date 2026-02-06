"""Main analysis pipeline."""

import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import AnalysisConfig, AnalysisContext
from .io.hashing import sha256_file
from .io.json_write import write_json
from .io.paths import ensure_directory, create_song_slug
from .custom_logging import setup_logging
from .models.schemas import RunRecord, StepRun, FailureRecord
from .steps import get_available_steps


class AnalysisPipeline:
    """Main analysis pipeline."""

    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.logger = None

    def analyze_song(self, song_path: Path, until_step: Optional[str] = None) -> RunRecord:
        """Run the full analysis pipeline on a song."""

        # Create context
        song_slug = create_song_slug(song_path.name)
        output_dir = self.config.metadata_dir / song_slug
        temp_dir = self.config.temp_dir / song_slug

        context = AnalysisContext(
            config=self.config,
            song_path=song_path,
            song_slug=song_slug,
            output_dir=output_dir,
            temp_dir=temp_dir,
            run_timestamp=datetime.utcnow()
        )

        # Setup logging
        log_file = temp_dir / f"run_{int(time.time())}.log"
        ensure_directory(log_file.parent)
        self.logger = setup_logging(log_file)

        self.logger.info(f"Starting analysis of {song_path} (slug: {song_slug})")

        # Ensure directories exist
        context.ensure_dirs()

        # Get available steps
        available_steps = get_available_steps()
        steps_to_run = self._get_steps_to_run(available_steps, until_step)

        # Run steps
        step_runs = []
        for step_name in steps_to_run:
            step_run = self._run_step(step_name, context)
            step_runs.append(step_run)

            if step_run.status == "failed" and not step_run.failure.retryable:
                self.logger.warning(f"Step {step_name} failed, continuing...")

        # Create run record
        run_record = RunRecord(
            schema_version="1.0",
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            song={
                "filename": song_path.name,
                "song_slug": song_slug,
                "sha256": sha256_file(song_path)
            },
            environment=self._get_environment_info(),
            steps=step_runs
        )

        # Write run record
        run_path = context.analysis_dir / "run.json"
        write_json(run_record.dict(), run_path, self.config.json_precision)

        self.logger.info(f"Analysis complete. Run record written to {run_path}")
        return run_record

    def _get_steps_to_run(self, available_steps: List[str], until_step: Optional[str]) -> List[str]:
        """Get the list of steps to run."""
        if until_step:
            if until_step not in available_steps:
                raise ValueError(f"Unknown step: {until_step}")
            idx = available_steps.index(until_step)
            return available_steps[:idx + 1]
        return available_steps

    def _run_step(self, step_name: str, context: AnalysisContext) -> StepRun:
        """Run a single step."""
        start_time = time.time()

        try:
            # Import and run the step
            module = __import__(f"song_analyzer.steps.step_{step_name}", fromlist=["run"])
            result = module.run(context)

            status = "failed" if result.failure else "ok"
            artifacts = [str(p) for p in result.artifacts_written]

            if result.failure:
                self.logger.error(f"Step {step_name} failed: {result.failure.message}")
            else:
                self.logger.info(f"Step {step_name} completed successfully")

            for warning in result.warnings:
                self.logger.warning(f"Step {step_name}: {warning}")

        except Exception as e:
            self.logger.exception(f"Step {step_name} raised exception")
            result = None
            status = "failed"
            failure = FailureRecord(
                code="UNKNOWN",
                message=str(e),
                exception_type=type(e).__name__,
                retryable=False
            )
            artifacts = []

        elapsed = time.time() - start_time

        return StepRun(
            name=step_name,
            status=status,
            artifacts=artifacts,
            seconds=round(elapsed, 2),
            failure=result.failure if result and result.failure else (failure if 'failure' in locals() else None)
        )

    def _get_environment_info(self) -> dict:
        """Get environment information."""
        import platform
        import sys
        import torch

        return {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.system().lower(),
            "cuda_available": torch.cuda.is_available(),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "packages": {
                "torch": torch.__version__,
            }
        }