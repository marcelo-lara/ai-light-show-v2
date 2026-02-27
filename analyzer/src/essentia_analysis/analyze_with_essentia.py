from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import essentia.standard as es
import numpy as np

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
    sample_rate: int = 44100,
) -> Dict[str, Any]:
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

    key = "unknown"
    scale = "unknown"
    key_strength = 0.0
    try:
        key_extractor = es.KeyExtractor()
        key, scale, key_strength, *_ = key_extractor(audio)
    except Exception as exc:
        warn(f"Key extraction failed: {exc}")

    rhythm_descriptors = extract_rhythm_descriptors(audio)
    beats = np.array(rhythm_descriptors.get("beats_position", []), dtype=np.float32)
    beats_intervals = np.array(rhythm_descriptors.get("bpm_intervals", []), dtype=np.float32)
    bpm = float(rhythm_descriptors.get("bpm", 0.0))
    beats_confidence = float(rhythm_descriptors.get("confidence", 0.0))
    downbeats = beats[::4] if len(beats) >= 4 else beats

    onsets = []
    onset_rate_values = []
    try:
        frame_size = 1024
        hop_size = 512
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
    frame_size = 1024
    hop_size = 512
    windowing = es.Windowing(type="hann")
    fft = es.FFT()
    cartesian_to_polar = es.CartesianToPolar()

    # Loudness & Envelope
    loudness_values = []
    envelope_values = []
    loudness_alg = es.Loudness()
    envelope_alg = es.Envelope()
    for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
        loudness_values.append(float(loudness_alg(frame)))
        envelope_values.append(to_jsonable(envelope_alg(frame)))

    # Chroma HPCP
    hpcp_values = []
    spectral_peaks_alg = es.SpectralPeaks(sampleRate=sr)
    hpcp_alg = es.HPCP(size=12, referenceFrequency=440, harmonics=8, minFrequency=40, maxFrequency=5000, sampleRate=sr)
    spectrum_alg = es.Spectrum()
    for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
        spectrum = spectrum_alg(windowing(frame))
        frequencies, magnitudes = spectral_peaks_alg(spectrum)
        hpcp = hpcp_alg(frequencies, magnitudes)
        hpcp_values.append(to_jsonable(hpcp))

    # Mel-Frequency Bands
    mel_bands_values = []
    mel_bands_alg = es.MelBands(numberBands=40, sampleRate=sr)
    for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
        spectrum = spectrum_alg(windowing(frame))
        mel_bands = mel_bands_alg(spectrum)
        mel_bands_values.append(to_jsonable(mel_bands))

    # Spectral Centroid
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

    # Organize into separate artifacts
    artifacts = {
        "rhythm": data,  # Keep the old data for compatibility
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
    for artifact_name, data in artifacts.items():
        json_path = Path(out_dir) / f"{artifact_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(to_jsonable(data), f, indent=2)

    # Plot each artifact
    try:
        plot_essentia_analysis(
            audio,
            sr,
            np.array(artifacts["rhythm"]["rhythm"]["beats"]),
            np.array(artifacts["rhythm"]["rhythm"]["downbeats"]),
            artifacts["rhythm"]["onsets"]["rate"],
            artifacts["rhythm"]["beat_loudness"]["values"],
            Path(out_dir) / "rhythm.svg",
        )
    except Exception as exc:
        warn(f"Rhythm plotting failed: {exc}")
    try:
        plot_loudness_envelope(
            artifacts["loudness_envelope"]["times"],
            artifacts["loudness_envelope"]["loudness"],
            artifacts["loudness_envelope"]["envelope"],
            Path(out_dir) / "loudness_envelope.svg",
        )
    except Exception as exc:
        warn(f"Loudness envelope plotting failed: {exc}")
    try:
        plot_chroma_hpcp(
            artifacts["chroma_hpcp"]["times"],
            artifacts["chroma_hpcp"]["hpcp"],
            Path(out_dir) / "chroma_hpcp.svg",
        )
    except Exception as exc:
        warn(f"Chroma HPCP plotting failed: {exc}")
    try:
        plot_mel_bands(
            artifacts["mel_bands"]["times"],
            artifacts["mel_bands"]["mel_bands"],
            Path(out_dir) / "mel_bands.svg",
        )
    except Exception as exc:
        warn(f"Mel bands plotting failed: {exc}")
        # Create a dummy SVG or skip
    try:
        plot_spectral_centroid(
            artifacts["spectral_centroid"]["times"],
            artifacts["spectral_centroid"]["centroid"],
            Path(out_dir) / "spectral_centroid.svg",
        )
    except Exception as exc:
        warn(f"Spectral centroid plotting failed: {exc}")

    return artifacts
