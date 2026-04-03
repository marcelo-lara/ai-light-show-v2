from __future__ import annotations

from pathlib import Path
from typing import Any

from ..essentia_analysis import analyze_with_essentia, build_loudness_hints
from ..essentia_analysis.common import is_stem_worth_analyzing
from ..runtime.progress import ProgressCallback, emit_stage
from ..storage.song_meta import load_json_file, load_sections, song_meta_dir
from .common import autodetect_device, build_essentia_manifest, dump_json, meta_file_path, merge_json_file, read_sample_rate, warn

ESSENTIA_FEATURES = ("rhythm", "loudness_envelope", "chroma_hpcp", "mel_bands", "spectral_centroid")


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any] | None:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_root = Path(params.get("meta_path", "/app/meta")).expanduser().resolve()
    print(f"Running Essentia analysis for {song_path.name}")
    try:
        emit_stage(progress_callback, "essentia-analysis", "Start", 1, 4)
        if not song_path.exists() or not song_path.is_file():
            warn(f"Song file does not exist: {song_path}")
            return None
        if autodetect_device() != "cuda":
            warn("CUDA is not available; Essentia analysis will run on cpu")
        song_dir = song_meta_dir(song_path, meta_root)
        song_dir.mkdir(parents=True, exist_ok=True)
        meta_file = meta_file_path(song_path, meta_root)
        essentia_dir = song_dir / "essentia"
        essentia_dir.mkdir(parents=True, exist_ok=True)

        def emit_part_stage(event: dict[str, Any]) -> None:
            if progress_callback is not None:
                progress_callback(event)

        emit_stage(progress_callback, "essentia-analysis", "Analyze Mix", 2, 4, part_name="mix")
        part_artifacts = {
            "mix": analyze_with_essentia(str(song_path), str(essentia_dir), "mix", sample_rate=read_sample_rate(song_path), artifact_file_stems={feature: feature for feature in ESSENTIA_FEATURES}, progress_callback=emit_part_stage)
        }
        metadata = load_json_file(meta_file) if meta_file.exists() else {}
        stems_dir = metadata.get("stems_dir")
        stems = metadata.get("stems", [])
        if stems_dir and stems:
            stems_path = Path(stems_dir)
            for stem_name in ["bass", "drums", "vocals", "other"]:
                stem_file = stems_path / f"{stem_name}.wav"
                if stem_file.exists() and is_stem_worth_analyzing(str(stem_file)):
                    emit_stage(progress_callback, "essentia-analysis", "Analyze Stem", 2, 4, part_name=stem_name)
                    print(f"Analyzing stem: {stem_name}")
                    part_artifacts[stem_name] = analyze_with_essentia(
                        str(stem_file),
                        str(essentia_dir),
                        stem_name,
                        sample_rate=read_sample_rate(stem_file),
                        artifact_file_stems={feature: f"{stem_name}_{feature}" for feature in ESSENTIA_FEATURES},
                        progress_callback=emit_part_stage,
                    )
        hints_path = song_dir / "hints.json"
        emit_stage(progress_callback, "essentia-analysis", "Write Metadata", 3, 4)
        dump_json(hints_path, build_loudness_hints(part_artifacts, load_sections(song_dir)))
        merge_json_file(meta_file, {"artifacts": {"essentia": build_essentia_manifest(essentia_dir, part_artifacts, ESSENTIA_FEATURES), "hints_file": str(hints_path)}})
        emit_stage(progress_callback, "essentia-analysis", "Complete", 4, 4)
        print("Essentia analysis complete.")
        return part_artifacts
    except Exception as exc:
        emit_stage(progress_callback, "essentia-analysis", "Failed", 4, 4)
        warn(f"Essentia analysis failed: {exc}")
        return None


TASK = {
    "value": "essentia-analysis",
    "label": "Essentia Analysis",
    "description": "Generate Essentia feature JSON and plots.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}