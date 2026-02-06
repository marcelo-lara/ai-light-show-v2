"""Step 100: Plot analysis results - Generate visualization plots.

This step writes SVG plots into `<metadata>/<song_slug>/plots/` (sibling to
`analysis/` and `show_plan/`). It also generates waveform plots for each Demucs
stem.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..config import AnalysisContext
from ..models.schemas import StepResult


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_audio_mono(librosa, audio_path: Path, *, sr: int | None = None):
    # Keep original sample rate by default; force mono for consistent plots.
    return librosa.load(str(audio_path), sr=sr, mono=True)


def _apply_overlays(ax, *, sections: list[dict] | None, phrases: list[dict] | None, moments: list[dict] | None):
    # Sections boundaries
    if sections:
        for i, section in enumerate(sections):
            start = float(section.get("start_s", 0.0))
            label = section.get("label", f"section_{i}")
            ax.axvline(x=start, color="red", linestyle="--", linewidth=1, alpha=0.7)
            ax.text(
                start,
                0.95,
                str(label),
                rotation=90,
                verticalalignment="top",
                horizontalalignment="left",
                fontsize=7,
                transform=ax.get_xaxis_transform(),
            )

    # Vocal phrases
    if phrases:
        for phrase in phrases:
            start = float(phrase.get("start_s", 0.0))
            end = float(phrase.get("end_s", start))
            if end > start:
                ax.axvspan(start, end, color="yellow", alpha=0.18)

    # Show moments
    if moments:
        for moment in moments:
            time_s = moment.get("time_s")
            if time_s is None:
                continue
            ax.axvline(float(time_s), color="blue", linewidth=1, alpha=0.35)


def run(ctx: AnalysisContext) -> StepResult:
    """Run the plot analysis results step."""

    # Set matplotlib config dir to avoid permission issues
    matplotlib_cache_dir = ctx.temp_dir / "matplotlib_cache"
    matplotlib_cache_dir.mkdir(exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(matplotlib_cache_dir)

    import matplotlib

    matplotlib.use("Agg")  # Headless backend
    import matplotlib.pyplot as plt
    import librosa
    import librosa.display

    warnings: list[str] = []

    # Remove legacy plots directory under analysis/ (previous versions wrote PNG/SVG there)
    legacy_plots_dir = ctx.analysis_dir / "plots"
    if legacy_plots_dir.exists() and legacy_plots_dir.is_dir():
        try:
            for child in legacy_plots_dir.iterdir():
                if child.is_file():
                    child.unlink()
            legacy_plots_dir.rmdir()
        except Exception as e:
            warnings.append(f"Failed to remove legacy plots dir {legacy_plots_dir}: {type(e).__name__}: {e}")

    # Check if source audio exists
    source_wav = ctx.temp_dir / "audio" / "source.wav"
    if not source_wav.exists():
        return StepResult(
            failure={
                "code": "DEPENDENCY_ERROR",
                "message": f"Source audio not found: {source_wav}",
                "retryable": False,
            }
        )

    # Load source audio
    try:
        y_mix, sr_mix = _load_audio_mono(librosa, source_wav, sr=None)
    except Exception as e:
        return StepResult(
            failure={
                "code": "IO_ERROR",
                "message": f"Failed to load source audio: {str(e)}",
                "exception_type": type(e).__name__,
                "retryable": True,
            }
        )

    # Create plots directory (same level as analysis/ and show_plan/)
    plots_dir = ctx.output_dir / "plots"
    plots_dir.mkdir(exist_ok=True)

    artifacts_written: list[Path] = []

    # Load optional overlay artifacts
    sections_data = _safe_load_json(ctx.analysis_dir / "sections.json")
    vocals_data = _safe_load_json(ctx.analysis_dir / "vocals.json")
    moments_data = _safe_load_json(ctx.show_plan_dir / "moments.json")

    sections = sections_data.get("sections", []) if sections_data else None
    phrases = vocals_data.get("phrases", []) if vocals_data else None
    moments = moments_data.get("moments", []) if moments_data else None

    # ---- Stem waveform SVGs (4 plots) ----
    stems_json = ctx.analysis_dir / "stems.json"
    stems_data = _safe_load_json(stems_json)
    stem_paths: dict[str, str] = {}
    if stems_data and isinstance(stems_data.get("stems"), dict):
        stem_paths = stems_data["stems"]
    else:
        warnings.append(f"Missing or invalid stems.json: {stems_json}")

    for stem_name in ["drums", "bass", "vocals", "other"]:
        stem_path_str = stem_paths.get(stem_name)
        if not stem_path_str:
            warnings.append(f"Stem path missing for '{stem_name}'")
            continue

        stem_path = Path(stem_path_str)
        if not stem_path.exists():
            warnings.append(f"Stem file not found for '{stem_name}': {stem_path}")
            continue

        try:
            y_stem, sr_stem = _load_audio_mono(librosa, stem_path, sr=None)
            fig, ax = plt.subplots(figsize=(12, 4))
            librosa.display.waveshow(y_stem, sr=sr_stem, ax=ax, alpha=0.9)
            _apply_overlays(ax, sections=sections, phrases=phrases, moments=moments)
            ax.set_title(f"Stem Waveform: {stem_name}")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            plt.tight_layout()
            plot_path = plots_dir / f"{stem_name}.svg"
            plt.savefig(plot_path, format="svg", bbox_inches="tight")
            plt.close(fig)
            artifacts_written.append(plot_path)
        except Exception as e:
            warnings.append(f"Failed to plot stem '{stem_name}': {type(e).__name__}: {e}")

    # ---- Existing analysis plots, now as SVG ----

    # Plot beats
    beats_path = ctx.analysis_dir / "beats.json"
    beats_data = _safe_load_json(beats_path)
    if beats_data:
        try:
            beats = beats_data.get("beats", [])
            fig, ax = plt.subplots(figsize=(19.2, 2))
            librosa.display.waveshow(y_mix, sr=sr_mix, ax=ax, alpha=0.5)
            for beat in beats:
                ax.axvline(float(beat), color="red", linestyle="--", linewidth=1)
            ax.set_title("Beats")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            plt.tight_layout()
            plot_path = plots_dir / "beats.svg"
            plt.savefig(plot_path, format="svg", bbox_inches="tight")
            plt.close(fig)
            artifacts_written.append(plot_path)
        except Exception as e:
            warnings.append(f"Failed to plot beats: {type(e).__name__}: {e}")

    # Plot energy
    energy_path = ctx.analysis_dir / "energy.json"
    energy_data = _safe_load_json(energy_path)
    if energy_data:
        try:
            tracks = energy_data.get("tracks", {})
            fig, ax = plt.subplots(figsize=(19.2, 2))
            librosa.display.waveshow(y_mix, sr=sr_mix, ax=ax, alpha=0.35)
            colors = ["blue", "red", "green", "orange", "purple"]
            has_tracks = False
            for i, (track_name, track_data) in enumerate(tracks.items()):
                if not isinstance(track_data, dict):
                    continue
                times = track_data.get("times_s") or track_data.get("times") or []
                values = track_data.get("values") or []
                if times and values:
                    color = colors[i % len(colors)]
                    ax.plot(times, values, color=color, linewidth=1, label=track_name)
                    has_tracks = True
            ax.set_title("Energy")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude / Energy")
            if has_tracks:
                ax.legend(loc="upper right", fontsize=8)
            plt.tight_layout()
            plot_path = plots_dir / "energy.svg"
            plt.savefig(plot_path, format="svg", bbox_inches="tight")
            plt.close(fig)
            artifacts_written.append(plot_path)
        except Exception as e:
            warnings.append(f"Failed to plot energy: {type(e).__name__}: {e}")

    # Plot sections (correctly spans time on x-axis)
    sections_path = ctx.analysis_dir / "sections.json"
    if sections_data:
        try:
            fig, ax = plt.subplots(figsize=(19.2, 2))
            librosa.display.waveshow(y_mix, sr=sr_mix, ax=ax, alpha=0.5)
            for section in sections:
                start = float(section.get("start_s", 0.0))
                end = float(section.get("end_s", start))
                label = str(section.get("label", ""))
                if end > start:
                    ax.axvspan(start, end, color="green", alpha=0.12)
                if label:
                    ax.text(
                        (start + end) / 2.0,
                        0.92,
                        label,
                        ha="center",
                        va="top",
                        fontsize=8,
                        transform=ax.get_xaxis_transform(),
                    )
            ax.set_title("Sections")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            plt.tight_layout()
            plot_path = plots_dir / "sections.svg"
            plt.savefig(plot_path, format="svg", bbox_inches="tight")
            plt.close(fig)
            artifacts_written.append(plot_path)
        except Exception as e:
            warnings.append(f"Failed to plot sections: {type(e).__name__}: {e}")

    # Plot vocals (highlight phrases)
    vocals_path = ctx.analysis_dir / "vocals.json"
    if vocals_data:
        try:
            fig, ax = plt.subplots(figsize=(19.2, 2))
            librosa.display.waveshow(y_mix, sr=sr_mix, ax=ax, alpha=0.5)
            for phrase in phrases:
                start = float(phrase.get("start_s", 0.0))
                end = float(phrase.get("end_s", start))
                if end > start:
                    ax.axvspan(start, end, color="yellow", alpha=0.2)
            ax.set_title("Vocals")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            plt.tight_layout()
            plot_path = plots_dir / "vocals.svg"
            plt.savefig(plot_path, format="svg", bbox_inches="tight")
            plt.close(fig)
            artifacts_written.append(plot_path)
        except Exception as e:
            warnings.append(f"Failed to plot vocals: {type(e).__name__}: {e}")

    return StepResult(artifacts_written=artifacts_written, warnings=warnings)