import sys
import os
import typer
from pathlib import Path
from .pipeline import run_pipeline, AnalysisConfig

app = typer.Typer(help="Song analysis pipeline CLI")


@app.command()
def analyze(
    song: str = typer.Argument(..., help="Path to song file relative to analyzer/ or absolute."),
    out: str = typer.Option("metadata/", help="Output metadata dir"),
    temp: str = typer.Option("temp_files/", help="Temp files dir"),
    device: str = typer.Option("auto", help="cuda|cpu|auto"),
    stems_model: str = typer.Option("demucs:htdemucs_ft", help="stems model spec"),
    overwrite: bool = typer.Option(False, help="Overwrite outputs if present"),
    until: str = typer.Option(None, help="Run until step name (e.g., stems, beats, energy)")
):
    """Analyze a song and emit LLM-friendly JSON artifacts.

    Run from the /analyzer folder for paths to resolve as in the backlog.
    """
    # Normalize paths to analyzer/ working dir
    workdir = Path(__file__).resolve().parents[1]
    song_path = Path(song)
    if not song_path.is_absolute():
        song_path = workdir / song_path
    cfg = AnalysisConfig(
        out_dir=Path(out),
        temp_dir=Path(temp),
        device=device,
        stems_model=stems_model,
        overwrite=overwrite,
        workdir=workdir,
    )
    run_pipeline(song_path, cfg, until=until)


@app.command()
def run_step(step: str, song: str = typer.Argument(...)):
    """Run a single step by name for debugging."""
    workdir = Path(__file__).resolve().parents[1]
    song_path = Path(song)
    if not song_path.is_absolute():
        song_path = workdir / song_path
    cfg = AnalysisConfig(out_dir=Path("metadata/"), temp_dir=Path("temp_files/"), device="auto", stems_model="demucs:htdemucs_ft", overwrite=False, workdir=workdir)
    run_pipeline(song_path, cfg, until=step)
