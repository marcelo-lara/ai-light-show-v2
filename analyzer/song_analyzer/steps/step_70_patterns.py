"""Step 70: Pattern mining - quantize drum events and find repeating patterns."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

from ..config import AnalysisContext
from ..io.json_write import write_json
from ..models.schemas import StepResult, PatternsArtifact

logger = logging.getLogger(__name__)


def run(ctx: AnalysisContext) -> StepResult:
    """Run pattern mining."""
    try:
        # Load required artifacts
        beats_data = _load_beats(ctx)
        onsets_data = _load_onsets(ctx)

        if not beats_data or not onsets_data:
            return StepResult(
                warnings=["Missing beats or onsets data, skipping pattern mining"]
            )

        # Extract drum events
        drum_events = _extract_drum_events(onsets_data)

        # Create quantization grid
        grid_info = _create_quantization_grid(beats_data)

        # Quantize events onto grid
        quantized_events = _quantize_events(drum_events, grid_info)

        # Build per-bar pattern vectors
        bar_patterns = _build_bar_patterns(quantized_events, grid_info)

        # Find repeating patterns
        patterns, occurrences = _find_repeating_patterns(bar_patterns, grid_info)

        # Create artifact
        artifact = PatternsArtifact(
            grid=grid_info,
            patterns=patterns,
            occurrences=occurrences
        )

        # Write artifact
        output_path = ctx.analysis_dir / "patterns.json"
        write_json(artifact.model_dump(), output_path)

        logger.info(f"Found {len(patterns)} patterns with {len(occurrences)} occurrences")

        return StepResult(artifacts_written=[output_path])

    except Exception as e:
        logger.exception("Pattern mining failed")
        return StepResult(
            failure={
                "code": "MODEL_ERROR",
                "message": f"Pattern mining failed: {e}",
                "exception_type": type(e).__name__,
                "retryable": False
            }
        )


def _load_beats(ctx: AnalysisContext) -> Optional[Dict[str, Any]]:
    """Load beats artifact."""
    beats_path = ctx.analysis_dir / "beats.json"
    if not beats_path.exists():
        return None

    with open(beats_path) as f:
        return json.load(f)


def _load_onsets(ctx: AnalysisContext) -> Optional[Dict[str, Any]]:
    """Load onsets artifact."""
    onsets_path = ctx.analysis_dir / "onsets.json"
    if not onsets_path.exists():
        return None

    with open(onsets_path) as f:
        return json.load(f)


def _extract_drum_events(onsets_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract drum events from onsets data."""
    events = []
    for event in onsets_data.get("events", []):
        # Focus on kick and snare events (high confidence drum hits)
        if event.get("strength", 0) > 0.3:  # Filter weak events
            events.append({
                "time": event["time"],
                "strength": event["strength"],
                "type": "drum"  # Could be refined to kick/snare if we had classification
            })
    return events


def _create_quantization_grid(beats_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create quantization grid based on beats."""
    beats = np.array(beats_data["beats"])
    tempo = beats_data["tempo"]["segments"][0]["bpm"]

    # Use 16th notes (4 per beat) for fine-grained patterns
    subdivisions_per_beat = 4
    beats_per_bar = 4  # Assume 4/4 time

    # Calculate grid spacing
    avg_beat_interval = np.mean(np.diff(beats))
    grid_spacing = avg_beat_interval / subdivisions_per_beat

    return {
        "tempo_bpm": tempo,
        "beats_per_bar": beats_per_bar,
        "subdivisions_per_beat": subdivisions_per_beat,
        "grid_spacing_s": grid_spacing,
        "total_beats": len(beats),
        "beat_times": beats.tolist()
    }


def _quantize_events(events: List[Dict[str, Any]], grid_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Quantize drum events onto the grid."""
    quantized = []

    for event in events:
        # Find nearest grid position
        time = event["time"]
        beat_times = np.array(grid_info["beat_times"])

        # Find which beat this event falls into
        beat_idx = np.searchsorted(beat_times, time) - 1
        if beat_idx < 0:
            beat_idx = 0
        elif beat_idx >= len(beat_times) - 1:
            continue

        # Calculate position within the beat (0-1)
        beat_start = beat_times[beat_idx]
        beat_end = beat_times[beat_idx + 1] if beat_idx + 1 < len(beat_times) else beat_start + grid_info["grid_spacing_s"] * grid_info["subdivisions_per_beat"]
        beat_duration = beat_end - beat_start

        if beat_duration > 0:
            position_in_beat = (time - beat_start) / beat_duration

            # Quantize to nearest subdivision
            subdivisions = grid_info["subdivisions_per_beat"]
            quantized_pos = round(position_in_beat * subdivisions) / subdivisions

            quantized.append({
                "beat_idx": int(beat_idx),
                "position_in_beat": quantized_pos,
                "strength": event["strength"],
                "time": time
            })

    return quantized


def _build_bar_patterns(quantized_events: List[Dict[str, Any]], grid_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build pattern vectors for each bar."""
    beats_per_bar = grid_info["beats_per_bar"]
    subdivisions = grid_info["subdivisions_per_beat"]
    total_beats = grid_info["total_beats"]

    bar_patterns = []

    # Process each bar
    for bar_start_beat in range(0, total_beats - beats_per_bar + 1, beats_per_bar):
        bar_events = []

        # Collect events for this bar
        for event in quantized_events:
            if bar_start_beat <= event["beat_idx"] < bar_start_beat + beats_per_bar:
                # Convert to bar-relative position
                relative_beat = event["beat_idx"] - bar_start_beat
                bar_position = relative_beat + event["position_in_beat"]
                bar_events.append({
                    "position": bar_position,
                    "strength": event["strength"]
                })

        # Create pattern vector (one-hot encoding of positions)
        pattern_vector = np.zeros(beats_per_bar * subdivisions)

        for event in bar_events:
            # Convert position to bin index
            bin_idx = int(event["position"] * subdivisions)
            if 0 <= bin_idx < len(pattern_vector):
                pattern_vector[bin_idx] = min(1.0, pattern_vector[bin_idx] + event["strength"])

        bar_patterns.append({
            "bar_idx": bar_start_beat // beats_per_bar,
            "start_beat": bar_start_beat,
            "vector": pattern_vector.tolist(),
            "event_count": len(bar_events)
        })

    return bar_patterns


def _find_repeating_patterns(bar_patterns: List[Dict[str, Any]], grid_info: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Find repeating patterns using clustering."""
    if len(bar_patterns) < 2:
        return [], []

    # Extract pattern vectors
    vectors = np.array([p["vector"] for p in bar_patterns])

    # Calculate similarity matrix
    similarity_matrix = cosine_similarity(vectors)

    # Find clusters of similar patterns
    clustering = DBSCAN(eps=0.8, min_samples=2, metric="precomputed")
    distance_matrix = 1 - similarity_matrix
    labels = clustering.fit_predict(distance_matrix)

    # Group patterns by cluster
    patterns = []
    occurrences = []

    for cluster_id in set(labels):
        if cluster_id == -1:  # Noise points
            continue

        # Get patterns in this cluster
        cluster_patterns = [
            bar_patterns[i] for i in range(len(bar_patterns))
            if labels[i] == cluster_id
        ]

        if len(cluster_patterns) < 2:
            continue

        # Create canonical pattern (average of cluster)
        canonical_vector = np.mean([p["vector"] for p in cluster_patterns], axis=0)

        # Create pattern entry
        pattern = {
            "id": f"pattern_{len(patterns)}",
            "vector": canonical_vector.tolist(),
            "cluster_size": len(cluster_patterns),
            "avg_events_per_bar": np.mean([p["event_count"] for p in cluster_patterns]),
            "label": _generate_pattern_label(canonical_vector, grid_info)
        }
        patterns.append(pattern)

        # Create occurrences
        for pattern_data in cluster_patterns:
            occurrences.append({
                "pattern_id": pattern["id"],
                "bar_idx": pattern_data["bar_idx"],
                "start_beat": pattern_data["start_beat"],
                "confidence": float(np.dot(canonical_vector, pattern_data["vector"]) / (np.linalg.norm(canonical_vector) * np.linalg.norm(pattern_data["vector"])))
            })

    # Sort occurrences by time
    occurrences.sort(key=lambda x: x["start_beat"])

    return patterns, occurrences


def _generate_pattern_label(vector: np.ndarray, grid_info: Dict[str, Any]) -> str:
    """Generate a human-readable label for a pattern."""
    beats_per_bar = grid_info["beats_per_bar"]
    subdivisions = grid_info["subdivisions_per_beat"]

    # Find positions with hits
    hit_positions = []
    for i, val in enumerate(vector):
        if val > 0.3:  # Threshold for considering it a hit
            beat = i // subdivisions
            sub = i % subdivisions
            hit_positions.append(f"{beat}.{sub}")

    if not hit_positions:
        return "empty"

    # Create a compact label
    if len(hit_positions) <= 4:
        return f"hits_at_{'_'.join(hit_positions)}"
    else:
        return f"complex_{len(hit_positions)}_hits"
