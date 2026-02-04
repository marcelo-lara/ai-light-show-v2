"""Command line interface for the song analyzer."""

import typer
from pathlib import Path

from .config import AnalysisConfig
from .pipeline import AnalysisPipeline


app = typer.Typer()


@app.command()
def analyze(
    song_path: Path = typer.Argument(..., help="Path to the MP3 file to analyze"),
    out: Path = typer.Option("metadata", help="Output directory for metadata"),
    temp: Path = typer.Option("temp_files", help="Temporary files directory"),
    device: str = typer.Option("auto", help="Device to use (auto/cuda/cpu)"),
    stems_model: str = typer.Option("htdemucs_ft", help="Stem separation model"),
    overwrite: bool = typer.Option(False, help="Overwrite existing results"),
    until: str = typer.Option(None, help="Run until this step (for incremental development)")
):
    """Analyze a song and generate metadata."""

    # Create config
    config = AnalysisConfig(
        songs_dir=song_path.parent,
        temp_dir=temp,
        metadata_dir=out,
        device=device,
        stems_model=stems_model,
        overwrite=overwrite
    )

    # Create and run pipeline
    pipeline = AnalysisPipeline(config)
    run_record = pipeline.analyze_song(song_path, until_step=until)

    # Print summary
    typer.echo(f"Analysis complete for {song_path.name}")
    typer.echo(f"Output written to {config.metadata_dir / run_record.song['song_slug']}")

    # Check for failures
    failed_steps = [step for step in run_record.steps if step.status == "failed"]
    if failed_steps:
        typer.echo(f"Warning: {len(failed_steps)} steps failed:")
        for step in failed_steps:
            typer.echo(f"  - {step.name}: {step.failure.message if step.failure else 'Unknown error'}")
        raise typer.Exit(1)


@app.command()
def run_step(
    step: str = typer.Argument(..., help="Step to run"),
    song_path: Path = typer.Argument(..., help="Path to the MP3 file"),
    out: Path = typer.Option("metadata", help="Output directory for metadata"),
    temp: Path = typer.Option("temp_files", help="Temporary files directory"),
    device: str = typer.Option("auto", help="Device to use (auto/cuda/cpu)"),
    stems_model: str = typer.Option("htdemucs_ft", help="Stem separation model"),
    overwrite: bool = typer.Option(False, help="Overwrite existing results")
):
    """Run a single analysis step."""

    # Create config
    config = AnalysisConfig(
        songs_dir=song_path.parent,
        temp_dir=temp,
        metadata_dir=out,
        device=device,
        stems_model=stems_model,
        overwrite=overwrite
    )

    # Create and run pipeline
    pipeline = AnalysisPipeline(config)
    run_record = pipeline.analyze_song(song_path, until_step=step)

    # Print summary
    typer.echo(f"Step {step} complete for {song_path.name}")


if __name__ == "__main__":
    app()