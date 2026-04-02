from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import essentia.standard as es
import numpy as np

from ..runtime.progress import ProgressCallback, emit_stage
from .common import to_jsonable, warn
from .extract_rhythm_descriptors import extract_rhythm_descriptors
from .plot_essentia_analysis import (
    plot_chroma_hpcp,
    plot_essentia_analysis,
    plot_loudness_envelope,
    plot_mel_bands,
    plot_spectral_centroid,
)


def analyze_with_essentia(
    audio_path: str,
    out_dir: str,
    part_name: str,
    sample_rate: int | None = None,
    artifact_file_stems: dict[str, str] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> Dict[str, Any]:
    artifact_file_stems = artifact_file_stems or {}
    stages = [
        "Load Audio",
        "Extract Key",
        "Extract Rhythm",
        "Detect Onsets",
        "Beat Loudness",
        "Loudness & Envelope",
        "Chroma HPCP",
        "Mel Bands",
        "Spectral Centroid",
        "Build Artifacts",
        "Write Rhythm JSON",
        "Write Loudness Envelope JSON",
        "Write Chroma HPCP JSON",
        "Write Mel Bands JSON",
        "Write Spectral Centroid JSON",
        "Plot Rhythm",
        "Plot Loudness Envelope",
        "Plot Chroma HPCP",
        "Plot Mel Bands",
        "Plot Spectral Centroid",
    ]
    step_total = len(stages)

    def report(stage: str) -> None:
        emit_stage(
            progress_callback,
            "essentia-analysis",
            stage,
            stages.index(stage) + 1,
            step_total,
            part_name=part_name,
        )

    def artifact_path(name: str, suffix: str) -> Path:
        file_stem = artifact_file_stems.get(name, name)
        return Path(out_dir) / f"{file_stem}.{suffix}"

    report("Load Audio")
    loader = es.AudioLoader(filename=audio_path)
    audio, sr, *_ = loader()
    duration = len(audio) / sr

    if sample_rate and sr != sample_rate:
        warn(
            f"Requested sample_rate={sample_rate}, but loaded audio at sample_rate={sr}; using loaded value"
        )

    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    audio = audio.astype(np.float32)

    frame_size = 1024
    hop_size = 512
    spectrum_size = (frame_size // 2) + 1

    report("Extract Key")
    key = "unknown"
    scale = "unknown"
    key_strength = 0.0
    try:
        key_extractor = es.KeyExtractor()
        key, scale, key_strength, *_ = key_extractor(audio)
    except Exception as exc:
        warn(f"Key extraction failed: {exc}")

    report("Extract Rhythm")
    rhythm_descriptors = extract_rhythm_descriptors(audio)
    beats = np.array(rhythm_descriptors.get("beats_position", []), dtype=np.float32)
    beats_intervals = np.array(rhythm_descriptors.get("bpm_intervals", []), dtype=np.float32)
    bpm = float(rhythm_descriptors.get("bpm", 0.0))
    beats_confidence = float(rhythm_descriptors.get("confidence", 0.0))
    downbeats = beats[::4] if len(beats) >= 4 else beats

    report("Detect Onsets")
    onsets = []
    onset_rate_values = []
    try:
        windowing = es.Windowing(type="hann")
        fft = es.FFT()
        cartesian_to_polar = es.CartesianToPolar()
        onset_detector = es.OnsetDetection(method="hfc")

        onset_flux = []
        for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
            fft_complex = fft(windowing(frame))
            magnitude, phase = cartesian_to_polar(fft_complex)
            onset_flux.append(float(onset_detector(magnitude, phase)))

        if onset_flux:
            onsets = list(es.Onsets()(np.array([onset_flux], dtype=np.float32), [1]))
            onset_rate_values = onset_flux
    except Exception as exc:
        warn(f"Onset detection failed: {exc}")

    report("Beat Loudness")
    beat_loudness = []
    rms = es.RMS()
    for i, beat_time in enumerate(beats):
        start_sample = int(beat_time * sr)
        end_sample = int(min((beat_time + beats_intervals[i]) * sr, len(audio))) if i < len(beats_intervals) else len(audio)
        if start_sample < end_sample:
            window = audio[start_sample:end_sample]
            loudness = rms(window)
            beat_loudness.append(float(loudness))
        else:
            beat_loudness.append(0.0)

    # New analyses: frame-wise computations
    windowing = es.Windowing(type="hann")

    # Loudness & Envelope
    report("Loudness & Envelope")
    loudness_values = []
    envelope_values = []
    loudness_alg = es.Loudness()
    envelope_alg = es.Envelope()
    for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
        loudness_values.append(float(loudness_alg(frame)))
        envelope_values.append(to_jsonable(envelope_alg(frame)))

    # Chroma HPCP
    report("Chroma HPCP")
    hpcp_values = []
    spectral_peaks_alg = es.SpectralPeaks(sampleRate=sr)
    hpcp_alg = es.HPCP(size=12, referenceFrequency=440, harmonics=8, minFrequency=40, maxFrequency=5000, sampleRate=sr)
    spectrum_alg = es.Spectrum(size=frame_size)
    for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
        spectrum = spectrum_alg(windowing(frame))
        frequencies, magnitudes = spectral_peaks_alg(spectrum)
        hpcp = hpcp_alg(frequencies, magnitudes)
        hpcp_values.append(to_jsonable(hpcp))

    # Mel-Frequency Bands
    report("Mel Bands")
    mel_bands_values = []
    mel_bands_alg = es.MelBands(numberBands=40, sampleRate=sr, inputSize=spectrum_size)
    for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
        spectrum = spectrum_alg(windowing(frame))
        mel_bands = mel_bands_alg(spectrum)
        mel_bands_values.append(to_jsonable(mel_bands))

    # Spectral Centroid
    report("Spectral Centroid")
    centroid_values = []
    centroid_alg = es.Centroid()
    for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
        spectrum = spectrum_alg(windowing(frame))
        centroid = centroid_alg(spectrum)
        centroid_values.append(float(centroid))

    # Time axis for frame-wise features
    times = [i * hop_size / sr for i in range(len(loudness_values))]

    data = {
        "part": part_name,
        "sample_rate": sr,
        "duration": duration,
        "key": {
            "key": key,
            "scale": scale,
            "strength": float(key_strength),
        },
        "rhythm": {
            "bpm": float(bpm),
            "beats": to_jsonable(list(beats)),
            "downbeats": to_jsonable(list(downbeats)),
            "tempo_confidence": float(beats_confidence),
            "beat_intervals": to_jsonable(list(beats_intervals)),
        },
        "rhythm_descriptors": rhythm_descriptors,
        "onsets": {
            "times": to_jsonable(list(onsets)),
            "rate": to_jsonable(list(onset_rate_values)),
        },
        "beat_loudness": {
            "values": to_jsonable(beat_loudness),
            "mean": float(np.mean(beat_loudness)) if beat_loudness else 0.0,
            "std": float(np.std(beat_loudness)) if beat_loudness else 0.0,
        },
    }

    artifacts = {
        "rhythm": data,
        "loudness_envelope": {
            "part": part_name,
            "sample_rate": sr,
            "duration": duration,
            "frame_size": frame_size,
            "hop_size": hop_size,
            "times": to_jsonable(times),
            "loudness": to_jsonable(loudness_values),
            "envelope": to_jsonable(envelope_values),
        },
        "chroma_hpcp": {
            "part": part_name,
            "sample_rate": sr,
            "duration": duration,
            "frame_size": frame_size,
            "hop_size": hop_size,
            "times": to_jsonable(times),
            "hpcp": hpcp_values,
        },
        "mel_bands": {
            "part": part_name,
            "sample_rate": sr,
            "duration": duration,
            "frame_size": frame_size,
            "hop_size": hop_size,
            "times": to_jsonable(times),
            "mel_bands": mel_bands_values,
        },
        "spectral_centroid": {
            "part": part_name,
            "sample_rate": sr,
            "duration": duration,
            "frame_size": frame_size,
            "hop_size": hop_size,
            "times": to_jsonable(times),
            "centroid": to_jsonable(centroid_values),
        },
    }

    # Write each artifact JSON
    report("Build Artifacts")
    write_stages = {
        "rhythm": "Write Rhythm JSON",
        "loudness_envelope": "Write Loudness Envelope JSON",
        "chroma_hpcp": "Write Chroma HPCP JSON",
        "mel_bands": "Write Mel Bands JSON",
        "spectral_centroid": "Write Spectral Centroid JSON",
    }
    for artifact_name, data in artifacts.items():
        report(write_stages[artifact_name])
        json_path = artifact_path(artifact_name, "json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(to_jsonable(data), f, indent=2)

    # Plot each artifact
    try:
        report("Plot Rhythm")
        plot_essentia_analysis(
            audio,
            sr,
            np.array(artifacts["rhythm"]["rhythm"]["beats"]),
            np.array(artifacts["rhythm"]["rhythm"]["downbeats"]),
            artifacts["rhythm"]["onsets"]["rate"],
            artifacts["rhythm"]["beat_loudness"]["values"],
            artifact_path("rhythm", "svg"),
        )
    except Exception as exc:
        warn(f"Rhythm plotting failed: {exc}")
    try:
        report("Plot Loudness Envelope")
        plot_loudness_envelope(
            artifacts["loudness_envelope"]["times"],
            artifacts["loudness_envelope"]["loudness"],
            artifacts["loudness_envelope"]["envelope"],
            artifact_path("loudness_envelope", "svg"),
        )
    except Exception as exc:
        warn(f"Loudness envelope plotting failed: {exc}")
    try:
        report("Plot Chroma HPCP")
        plot_chroma_hpcp(
            artifacts["chroma_hpcp"]["times"],
            artifacts["chroma_hpcp"]["hpcp"],
            artifact_path("chroma_hpcp", "svg"),
        )
    except Exception as exc:
        warn(f"Chroma HPCP plotting failed: {exc}")
    try:
        report("Plot Mel Bands")
        plot_mel_bands(
            artifacts["mel_bands"]["times"],
            artifacts["mel_bands"]["mel_bands"],
            artifact_path("mel_bands", "svg"),
        )
    except Exception as exc:
        warn(f"Mel bands plotting failed: {exc}")
        # Create a dummy SVG or skip
    try:
        report("Plot Spectral Centroid")
        plot_spectral_centroid(
            artifacts["spectral_centroid"]["times"],
            artifacts["spectral_centroid"]["centroid"],
            artifact_path("spectral_centroid", "svg"),
        )
    except Exception as exc:
        warn(f"Spectral centroid plotting failed: {exc}")

    return artifacts
