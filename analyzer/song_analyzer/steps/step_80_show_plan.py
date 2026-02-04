"""Phase 8: Show Plan IR - Create LLM-friendly show plan from all analysis artifacts."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from song_analyzer.models.schemas import StepResult

logger = logging.getLogger(__name__)


class MusicalRole(BaseModel):
    """A musical role mapping tracks to features."""
    primary: str = Field(..., description="Primary track for this role")
    features: List[str] = Field(default_factory=list, description="Features associated with this role")


class Moment(BaseModel):
    """A notable moment in the song."""
    time_s: float = Field(..., description="Time in seconds")
    type: str = Field(..., description="Type of moment (drop, riser, vocal_entry, energy_peak, etc.)")
    strength: float = Field(..., description="Confidence/strength of the moment (0-1)")
    evidence: List[str] = Field(default_factory=list, description="Evidence supporting this moment")


class ShowPlanMeta(BaseModel):
    """Metadata for the show plan."""
    style: str = Field(default="unknown", description="Detected musical style")
    llm_version: str = Field(default="unknown", description="LLM version used for analysis")
    confidence: float = Field(default=0.0, description="Overall confidence in the analysis")
    notes: str = Field(default="", description="Additional notes")


def run(ctx) -> StepResult:
    """Create LLM-friendly show plan from all analysis artifacts."""
    try:
        # Load all available analysis artifacts
        artifacts = _load_analysis_artifacts(ctx.output_dir / "analysis")

        # Generate roles mapping
        roles = _generate_roles(artifacts)

        # Generate notable moments
        moments = _generate_moments(artifacts)

        # Generate show plan index
        show_plan = _generate_show_plan(ctx, artifacts)

        # Write outputs
        show_plan_dir = ctx.output_dir / "show_plan"
        show_plan_dir.mkdir(exist_ok=True)

        # Write roles.json
        roles_path = show_plan_dir / "roles.json"
        with open(roles_path, 'w', encoding='utf-8') as f:
            json.dump({
                "schema_version": "1.0",
                "generated_at": ctx.run_timestamp.isoformat(),
                "roles": {k: v.dict() for k, v in roles.items()}
            }, f, indent=2, ensure_ascii=False)

        # Write moments.json
        moments_path = show_plan_dir / "moments.json"
        with open(moments_path, 'w', encoding='utf-8') as f:
            json.dump({
                "schema_version": "1.0",
                "generated_at": ctx.run_timestamp.isoformat(),
                "moments": [m.dict() for m in moments]
            }, f, indent=2, ensure_ascii=False)

        # Write show_plan.json
        show_plan_path = show_plan_dir / "show_plan.json"
        with open(show_plan_path, 'w', encoding='utf-8') as f:
            json.dump(show_plan, f, indent=2, ensure_ascii=False)

        artifacts_written = [str(roles_path), str(moments_path), str(show_plan_path)]
        logger.info(f"Show plan created with {len(roles)} roles and {len(moments)} moments")

        return StepResult(
            artifacts_written=artifacts_written,
            warnings=[],
            failure=None
        )

    except Exception as e:
        logger.exception("Show plan generation failed")
        return StepResult(
            artifacts_written=[],
            warnings=[],
            failure={
                "code": "ANALYSIS_ERROR",
                "message": f"Show plan generation failed: {str(e)}",
                "detail": str(e),
                "exception_type": type(e).__name__,
                "retryable": False
            }
        )


def _load_analysis_artifacts(analysis_dir: Path) -> Dict[str, Any]:
    """Load all available analysis artifacts."""
    artifacts = {}

    # List of possible artifact files
    artifact_files = [
        "timeline.json",
        "stems.json",
        "beats.json",
        "energy.json",
        "onsets.json",
        "vocals.json",
        "sections.json",
        "patterns.json"
    ]

    for filename in artifact_files:
        filepath = analysis_dir / filename
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    artifacts[filename.replace('.json', '')] = json.load(f)
                logger.debug(f"Loaded artifact: {filename}")
            except Exception as e:
                logger.warning(f"Failed to load {filename}: {e}")

    return artifacts


def _generate_roles(artifacts: Dict[str, Any]) -> Dict[str, MusicalRole]:
    """Generate musical roles mapping from available artifacts."""
    roles = {}

    # Always include groove role if we have drum data
    if 'onsets' in artifacts or 'beats' in artifacts:
        roles['groove'] = MusicalRole(
            primary="drums",
            features=["beats", "kick", "snare", "patterns"]
        )

    # Include bass role if we have stems
    if 'stems' in artifacts:
        stem_names = artifacts['stems'].get('stems', [])
        if 'bass' in stem_names:
            roles['bass'] = MusicalRole(
                primary="bass",
                features=["energy", "low_end"]
            )

    # Include lead/vocals role if we have vocal data
    if 'vocals' in artifacts:
        roles['lead'] = MusicalRole(
            primary="vocals",
            features=["phrases", "energy", "sections"]
        )

    # Include harmony role for other stems
    if 'stems' in artifacts:
        stem_names = artifacts['stems'].get('stems', [])
        harmony_stems = [s for s in stem_names if s not in ['drums', 'bass', 'vocals']]
        if harmony_stems:
            roles['harmony'] = MusicalRole(
                primary=harmony_stems[0],  # Use first non-primary stem
                features=["texture", "energy"]
            )

    # If no roles detected, provide a minimal fallback
    if not roles:
        roles['unknown'] = MusicalRole(
            primary="mix",
            features=["energy", "sections"]
        )

    return roles


def _generate_moments(artifacts: Dict[str, Any]) -> List[Moment]:
    """Generate notable moments from analysis artifacts."""
    moments = []

    # Energy-based moments
    if 'energy' in artifacts:
        moments.extend(_extract_energy_moments(artifacts['energy']))

    # Section change moments
    if 'sections' in artifacts:
        moments.extend(_extract_section_moments(artifacts['sections']))

    # Vocal entry moments
    if 'vocals' in artifacts:
        moments.extend(_extract_vocal_moments(artifacts['vocals']))

    # Pattern-based moments
    if 'patterns' in artifacts:
        moments.extend(_extract_pattern_moments(artifacts['patterns']))

    # Sort moments by time
    moments.sort(key=lambda m: m.time_s)

    # Remove duplicates (moments too close together)
    filtered_moments = []
    for moment in moments:
        # Check if this moment is too close to existing ones
        too_close = False
        for existing in filtered_moments:
            if abs(moment.time_s - existing.time_s) < 2.0:  # 2 second minimum separation
                too_close = True
                break
        if not too_close:
            filtered_moments.append(moment)

    return filtered_moments


def _extract_energy_moments(energy_data: Dict[str, Any]) -> List[Moment]:
    """Extract moments from energy analysis."""
    moments = []

    if 'curve' not in energy_data:
        return moments

    curve = np.array(energy_data['curve'])
    times = np.array(energy_data.get('times', []))
    if len(times) != len(curve):
        return moments

    # Find significant energy peaks
    mean_energy = np.mean(curve)
    std_energy = np.std(curve)
    threshold = mean_energy + 1.5 * std_energy

    peak_indices = []
    for i in range(1, len(curve) - 1):
        if curve[i] > threshold and curve[i] > curve[i-1] and curve[i] > curve[i+1]:
            peak_indices.append(i)

    for idx in peak_indices:
        time_s = float(times[idx])
        strength = min(1.0, (curve[idx] - mean_energy) / (3 * std_energy))
        moments.append(Moment(
            time_s=time_s,
            type="energy_peak",
            strength=strength,
            evidence=["energy_analysis"]
        ))

    return moments


def _extract_section_moments(sections_data: Dict[str, Any]) -> List[Moment]:
    """Extract moments from section analysis."""
    moments = []

    sections = sections_data.get('sections', [])
    for section in sections:
        if 'start_s' in section:
            time_s = float(section['start_s'])
            section_type = section.get('label', 'unknown')
            confidence = section.get('confidence', 0.5)

            # Map section types to moment types
            moment_type = "section_change"
            if "drop" in section_type.lower():
                moment_type = "drop"
            elif "build" in section_type.lower() or "riser" in section_type.lower():
                moment_type = "riser"
            elif "break" in section_type.lower():
                moment_type = "break"

            moments.append(Moment(
                time_s=time_s,
                type=moment_type,
                strength=confidence,
                evidence=["section_analysis", f"section_type:{section_type}"]
            ))

    return moments


def _extract_vocal_moments(vocals_data: Dict[str, Any]) -> List[Moment]:
    """Extract moments from vocal analysis."""
    moments = []

    # Look for vocal activity starts
    vad_segments = vocals_data.get('vad_segments', [])
    for segment in vad_segments:
        if 'start_s' in segment and segment.get('confidence', 0) > 0.7:
            time_s = float(segment['start_s'])
            moments.append(Moment(
                time_s=time_s,
                type="vocal_entry",
                strength=float(segment['confidence']),
                evidence=["vad_analysis"]
            ))

    # Look for vocal phrases
    phrases = vocals_data.get('phrases', [])
    for phrase in phrases:
        if 'start_s' in phrase:
            time_s = float(phrase['start_s'])
            confidence = phrase.get('confidence', 0.5)
            moments.append(Moment(
                time_s=time_s,
                type="vocal_phrase",
                strength=confidence,
                evidence=["phrase_detection"]
            ))

    return moments


def _extract_pattern_moments(patterns_data: Dict[str, Any]) -> List[Moment]:
    """Extract moments from pattern analysis."""
    moments = []

    occurrences = patterns_data.get('occurrences', [])
    for occurrence in occurrences:
        if 'start_beat' in occurrence and occurrence.get('confidence', 0) > 0.6:
            # Convert beat time to seconds (rough approximation)
            # This would need proper beat timing from beats.json
            start_beat = float(occurrence['start_beat'])
            # Approximate: assume 120 BPM = 0.5 seconds per beat
            time_s = start_beat * 0.5

            moments.append(Moment(
                time_s=time_s,
                type="pattern_repeat",
                strength=float(occurrence['confidence']),
                evidence=["pattern_analysis", f"pattern_id:{occurrence.get('pattern_id', 'unknown')}"]
            ))

    return moments


def _generate_show_plan(ctx, artifacts: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the main show plan index."""
    # Build includes mapping
    includes = {}

    # Analysis artifacts
    analysis_artifacts = [
        "timeline", "stems", "beats", "energy", "onsets", "vocals", "sections", "patterns"
    ]
    for artifact in analysis_artifacts:
        if artifact in artifacts:
            includes[artifact] = f"../analysis/{artifact}.json"

    # Show plan artifacts
    show_plan_artifacts = ["roles", "moments"]
    for artifact in show_plan_artifacts:
        includes[artifact] = f"./{artifact}.json"

    # Try to infer musical style from available data
    style = _infer_musical_style(artifacts)

    return {
        "schema_version": "1.0",
        "generated_at": ctx.run_timestamp.isoformat(),
        "includes": includes,
        "meta": {
            "style": style,
            "llm_version": "unknown",  # Placeholder for future LLM integration
            "confidence": 0.0,  # Placeholder until scoring is implemented
            "notes": "Show plan generated from available analysis artifacts"
        }
    }


def _infer_musical_style(artifacts: Dict[str, Any]) -> str:
    """Make a basic inference about musical style."""
    # Very basic style detection based on available features
    has_drums = 'onsets' in artifacts or 'beats' in artifacts
    has_vocals = 'vocals' in artifacts
    has_sections = 'sections' in artifacts

    if has_vocals and has_drums:
        return "electronic_vocal"
    elif has_drums and not has_vocals:
        return "electronic_instrumental"
    elif has_sections:
        return "structured"
    else:
        return "unknown"