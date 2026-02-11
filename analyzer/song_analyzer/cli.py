"""Command line interface for the song analyzer."""

from __future__ import annotations

from pathlib import Path
import glob
import os

import typer

from .config import AnalysisConfig
from .pipeline import AnalysisPipeline
from .utils.numba_guard import disable_numba_jit


os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
disable_numba_jit()


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


@app.command()
def analyze_all(
    songs_dir: Path = typer.Argument(..., help="Directory containing MP3 files to analyze"),
    out: Path = typer.Option("metadata", help="Output directory for metadata"),
    temp: Path = typer.Option("temp_files", help="Temporary files directory"),
    device: str = typer.Option("auto", help="Device to use (auto/cuda/cpu)"),
    stems_model: str = typer.Option("htdemucs_ft", help="Stem separation model"),
    overwrite: bool = typer.Option(False, help="Overwrite existing results"),
    until: str = typer.Option(None, help="Run until this step (for incremental development)")
):
    """Analyze all songs in the directory."""

    # Find all MP3 files
    mp3_files = list(songs_dir.glob("*.mp3"))
    if not mp3_files:
        typer.echo(f"No MP3 files found in {songs_dir}")
        return

    typer.echo(f"Found {len(mp3_files)} MP3 files to analyze")

    # Create config
    config = AnalysisConfig(
        songs_dir=songs_dir,
        temp_dir=temp,
        metadata_dir=out,
        device=device,
        stems_model=stems_model,
        overwrite=overwrite
    )

    # Create pipeline
    pipeline = AnalysisPipeline(config)

    failed_songs = []
    for song_path in mp3_files:
        typer.echo(f"Analyzing {song_path.name}...")
        try:
            run_record = pipeline.analyze_song(song_path, until_step=until)
            typer.echo(f"Completed {song_path.name}")
        except Exception as e:
            typer.echo(f"Failed {song_path.name}: {e}")
            failed_songs.append(song_path.name)

    if failed_songs:
        typer.echo(f"Analysis complete. Failed songs: {', '.join(failed_songs)}")
        raise typer.Exit(1)
    else:
        typer.echo("All songs analyzed successfully")


# -- Celery broker helper ---------------------------------------------------
import os
import time
import shlex
from kombu import Connection


@app.command()
def listen(
    broker: str = typer.Option(None, envvar="CELERY_BROKER_URL", help="Celery broker URL"),
    start_worker: bool = typer.Option(False, help="Start a Celery worker after broker is reachable"),
    concurrency: int = typer.Option(1, help="Worker concurrency if starting a worker"),
    worker_args: str = typer.Option(None, envvar="CELERY_WORKER_ARGS", help="Additional args for the celery worker command")
):
    """Wait for the Celery broker to become available and optionally start a worker.

    Uses Kombu's Connection to perform a broker-level connection check which is
    more accurate than a raw Redis ping (works for different broker backends).

    If `--start-worker` is passed, this will exec into the `celery` CLI so the
    container acts as the worker process. `worker_args` may be read from the
    `CELERY_WORKER_ARGS` env var when not provided on the CLI.
    """

    broker = broker or "redis://localhost:6379/0"
    worker_args = worker_args or os.environ.get("CELERY_WORKER_ARGS", "-A tasks.celery_app.celery_app worker --loglevel=info")

    typer.echo(f"Waiting for Celery broker at {broker} ...")
    while True:
        try:
            with Connection(broker) as conn:
                conn.connect()
            typer.echo("Broker is reachable")
            break
        except Exception as e:
            typer.echo(f"Broker not available yet: {e}")
            time.sleep(1)

    if start_worker:
        # Build the command and replace the current process with the celery worker
        cmd = shlex.split(worker_args)
        # Ensure celery binary is first if not specified
        if cmd[0] != "celery":
            cmd.insert(0, "celery")
        typer.echo(f"Starting Celery worker: {' '.join(cmd)}")
        os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    app()