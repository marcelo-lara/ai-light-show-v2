"""Step 60: Sections - Extract song structure using embeddings."""

from pathlib import Path
import numpy as np
import scipy.signal
from sklearn.metrics.pairwise import cosine_similarity

from ..config import AnalysisContext
from ..io.json_write import write_json
from ..models.schemas import StepResult, SectionsArtifact


def run(ctx: AnalysisContext) -> StepResult:
    """Run the sections step."""

    # Check if timeline exists
    timeline_json = ctx.analysis_dir / "timeline.json"
    if not timeline_json.exists():
        return StepResult(
            failure={
                "code": "DEPENDENCY_ERROR",
                "message": f"Timeline analysis not found: {timeline_json}",
                "retryable": False
            }
        )

    # Load timeline info
    import json
    with open(timeline_json) as f:
        timeline_data = json.load(f)

    # Get source audio path
    source_audio = timeline_data.get("source_audio", {}).get("decoded_wav")
    if not source_audio or not Path(source_audio).exists():
        return StepResult(
            failure={
                "code": "DEPENDENCY_ERROR",
                "message": f"Source audio not found: {source_audio}",
                "retryable": False
            }
        )

    # Extract sections
    sections = extract_sections(source_audio)

    # Create artifact
    sections_artifact = SectionsArtifact(
        schema_version="1.0",
        source={
            "name": "openl3_fallback" if sections and sections[0].get("confidence", 1.0) < 0.8 else "openl3",
            "model": "music_fallback" if sections and sections[0].get("confidence", 1.0) < 0.8 else "music",
            "device": ctx.config.device
        },
        sections=sections
    )

    # Write sections.json
    sections_path = ctx.analysis_dir / "sections.json"
    write_json(sections_artifact.dict(), sections_path, ctx.config.json_precision)

    return StepResult(artifacts_written=[sections_path])


def extract_sections(audio_path: str) -> list[dict]:
    """Extract song sections using OpenL3 embeddings and novelty detection."""

    try:
        import openl3
        import librosa
    except ImportError:
        # Fallback if OpenL3 not available
        return _fallback_sections(audio_path)

    try:
        # Set TensorFlow environment variables to help with GPU memory
        import os
        os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
        os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'

        # Load audio
        y, sr = librosa.load(audio_path, sr=48000)  # OpenL3 expects 48kHz

        # Extract embeddings with smaller batch size for lower memory GPUs
        emb, ts = openl3.get_audio_embedding(
            y, sr,
            model=None,  # Use default music model
            hop_size=1.0,  # 1 second windows
            batch_size=8  # Reduced from 32 to 8 for lower memory usage
        )

        # Compute self-similarity matrix
        similarity = cosine_similarity(emb)

        # Compute novelty curve (change detection)
        # Use checkerboard kernel for structural novelty
        kernel = np.array([[-1, -1], [1, 1]])
        novelty = scipy.signal.convolve2d(similarity, kernel, mode='valid')
        novelty = np.sum(np.abs(novelty), axis=1)

        # Normalize novelty
        novelty = (novelty - np.min(novelty)) / (np.max(novelty) - np.min(novelty) + 1e-8)

        # Find peaks in novelty curve (section boundaries)
        peaks, _ = scipy.signal.find_peaks(
            novelty,
            height=0.3,  # Minimum peak height
            distance=int(5 / 1.0),  # Minimum 5 seconds between boundaries
            prominence=0.1
        )

        # Convert peak indices to time
        boundary_times = ts[peaks]

        # Create sections
        sections = []
        start_time = 0.0

        # Add intro section
        sections.append({
            "start_s": 0.0,
            "end_s": float(boundary_times[0]) if len(boundary_times) > 0 else float(ts[-1]),
            "label": "intro",
            "confidence": 0.8
        })

        # Add intermediate sections
        for i, boundary in enumerate(boundary_times):
            if i == 0:
                continue  # Skip first boundary (already used for intro end)

            start_time = float(boundary_times[i-1]) if i > 0 else 0.0
            end_time = float(boundary)

            # Simple labeling based on position
            if i == 1:
                label = "verse"
            elif i == 2:
                label = "chorus"
            elif i == 3:
                label = "bridge"
            else:
                label = "section"

            sections.append({
                "start_s": start_time,
                "end_s": end_time,
                "label": label,
                "confidence": 0.7
            })

        # Add outro section
        if boundary_times.size > 0:
            sections.append({
                "start_s": float(boundary_times[-1]),
                "end_s": float(ts[-1]),
                "label": "outro",
                "confidence": 0.8
            })

        # Ensure sections cover the entire track
        if not sections:
            sections = [{
                "start_s": 0.0,
                "end_s": float(ts[-1]),
                "label": "main",
                "confidence": 0.5
            }]

        return sections

    except Exception as e:
        # If OpenL3 fails (memory, model issues, etc.), use fallback
        print(f"OpenL3 failed ({e}), using fallback section detection")
        return _fallback_sections(audio_path)


def _fallback_sections(audio_path: str) -> list[dict]:
    """Fallback section detection using energy and spectral features."""

    import librosa

    # Load audio
    y, sr = librosa.load(audio_path, sr=None)

    # Compute RMS energy with 1-second windows
    hop_length = sr
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    times = librosa.times_like(rms, sr=sr, hop_length=hop_length)

    # Compute spectral centroid for timbre changes
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]

    # Normalize features
    rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-8)
    centroid_norm = (centroid - np.min(centroid)) / (np.max(centroid) - np.min(centroid) + 1e-8)

    # Combine features for novelty
    combined = (rms_norm + centroid_norm) / 2

    # Simple peak detection for boundaries
    peaks, _ = scipy.signal.find_peaks(
        combined,
        height=0.4,
        distance=int(10),  # Minimum 10 seconds between sections
        prominence=0.1
    )

    boundary_times = times[peaks]

    # Create basic sections
    sections = []
    start_time = 0.0

    for boundary in boundary_times:
        sections.append({
            "start_s": float(start_time),
            "end_s": float(boundary),
            "label": "section",
            "confidence": 0.5
        })
        start_time = float(boundary)

    # Add final section
    sections.append({
        "start_s": float(start_time),
        "end_s": float(times[-1]),
        "label": "outro",
        "confidence": 0.5
    })

    return sections