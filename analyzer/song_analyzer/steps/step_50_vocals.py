"""Step 50: Vocals - Extract vocal activity and phrases."""

from pathlib import Path
import numpy as np
import torch
import onnxruntime as ort

from ..config import AnalysisContext
from ..io.json_write import write_json
from ..models.schemas import StepResult, VocalsArtifact


def run(ctx: AnalysisContext) -> StepResult:
    """Run the vocals step."""

    # Check if stems exist
    stems_json = ctx.analysis_dir / "stems.json"
    if not stems_json.exists():
        return StepResult(
            failure={
                "code": "DEPENDENCY_ERROR",
                "message": f"Stems analysis not found: {stems_json}",
                "retryable": False
            }
        )

    # Load stems info
    import json
    with open(stems_json) as f:
        stems_data = json.load(f)

    # Get vocals stem
    vocals_path = stems_data["stems"].get("vocals")
    if not vocals_path or not Path(vocals_path).exists():
        return StepResult(
            failure={
                "code": "DEPENDENCY_ERROR",
                "message": f"Vocals stem not found: {vocals_path}",
                "retryable": False
            }
        )

    # Extract vocal activity
    segments, phrases = extract_vocal_activity(vocals_path)

    # Create artifact
    vocals_artifact = VocalsArtifact(
        schema_version="1.0",
        source={
            "name": "silero_vad",
            "model": "silero_vad",
            "device": ctx.config.device,
            "fallback": "energy_based" if not segments else None
        },
        segments=segments,
        phrases=phrases
    )

    # Write vocals.json
    vocals_path_out = ctx.analysis_dir / "vocals.json"
    write_json(vocals_artifact.dict(), vocals_path_out, ctx.config.json_precision)

    return StepResult(artifacts_written=[vocals_path_out])


def extract_vocal_activity(audio_path: str) -> tuple[list[dict], list[dict]]:
    """Extract vocal activity segments and phrases from vocals stem using Silero VAD with fallback."""

    import librosa

    # Load audio at 16kHz for VAD
    y, sr = librosa.load(audio_path, sr=16000)

    # Load Silero VAD model
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False,
        onnx=False
    )

    # Get VAD function
    get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks = utils

    # Run VAD
    speech_timestamps = get_speech_timestamps(y, model, sampling_rate=16000)

    segments = []
    phrases = []

    if speech_timestamps:
        # Use VAD results if available
        for timestamp in speech_timestamps:
            start_s = timestamp['start'] / 16000.0
            end_s = timestamp['end'] / 16000.0
            duration = end_s - start_s

            if duration > 0.1:  # Minimum segment length
                segments.append({
                    "start_s": round(float(start_s), 3),
                    "end_s": round(float(end_s), 3),
                    "confidence": 1.0  # Silero VAD doesn't provide confidence
                })

                # Create phrase if segment is long enough
                if duration > 0.5:
                    phrases.append({
                        "start_s": round(float(start_s), 3),
                        "end_s": round(float(end_s), 3),
                        "type": "vocal_phrase",
                        "confidence": 1.0
                    })
    else:
        # Fallback: energy-based detection for low-volume vocal-like sounds
        # Load at original sample rate for better analysis
        y_orig, sr_orig = librosa.load(audio_path, sr=None)

        # Compute RMS energy with smaller hop size
        hop_length = int(sr_orig * 0.01)  # 10ms hops
        rms = librosa.feature.rms(y=y_orig, hop_length=hop_length)[0]
        times = librosa.times_like(rms, sr=sr_orig, hop_length=hop_length)

        # Very sensitive threshold for low-volume audio
        threshold = np.percentile(rms, 10)  # 10th percentile instead of 25th

        # If threshold is too low, use a minimum threshold
        min_threshold = 0.001  # Very low minimum
        threshold = max(threshold, min_threshold)

        vad_frames = rms > threshold

        # Find contiguous segments
        in_segment = False
        start_time = None
        start_idx = None

        for i, (time_s, is_active) in enumerate(zip(times, vad_frames)):
            if is_active and not in_segment:
                # Start of segment
                in_segment = True
                start_time = time_s
                start_idx = i
            elif not is_active and in_segment:
                # End of segment
                end_time = time_s
                duration = end_time - start_time

                if duration > 0.05:  # Shorter minimum for fallback
                    # Calculate confidence based on RMS
                    segment_rms = rms[start_idx:i]
                    confidence = float(np.mean(segment_rms > threshold))

                    segments.append({
                        "start_s": round(float(start_time), 3),
                        "end_s": round(float(end_time), 3),
                        "confidence": round(confidence, 3)
                    })

                    # Create phrase if segment is long enough
                    if duration > 0.3:  # Shorter for fallback
                        phrases.append({
                            "start_s": round(float(start_time), 3),
                            "end_s": round(float(end_time), 3),
                            "type": "vocal_phrase",
                            "confidence": round(confidence, 3)
                        })

                in_segment = False

        # Handle case where segment goes to end
        if in_segment and start_time is not None:
            end_time = times[-1]
            duration = end_time - start_time
            if duration > 0.05:
                segment_rms = rms[start_idx:]
                confidence = float(np.mean(segment_rms > threshold))
                segments.append({
                    "start_s": round(float(start_time), 3),
                    "end_s": round(float(end_time), 3),
                    "confidence": round(confidence, 3)
                })
                if duration > 0.3:
                    phrases.append({
                        "start_s": round(float(start_time), 3),
                        "end_s": round(float(end_time), 3),
                        "type": "vocal_phrase",
                        "confidence": round(confidence, 3)
                    })

    return segments, phrases