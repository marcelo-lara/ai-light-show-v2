from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np

essentia_module = importlib.import_module("src.essentia_analysis.analyze_with_essentia")


def test_analyze_with_essentia_emits_deterministic_stage_events(tmp_path: Path, monkeypatch) -> None:
    frames = [np.array([0.1, 0.2], dtype=np.float32), np.array([0.2, 0.3], dtype=np.float32)]

    fake_es = SimpleNamespace(
        AudioLoader=lambda filename: lambda: (np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32), 2),
        KeyExtractor=lambda: lambda audio: ("C", "major", 0.8),
        Windowing=lambda type: lambda frame: frame,
        FFT=lambda: lambda frame: frame,
        CartesianToPolar=lambda: lambda fft_complex: (fft_complex, fft_complex),
        OnsetDetection=lambda method: lambda magnitude, phase: 1.0,
        FrameGenerator=lambda audio, frameSize, hopSize, startFromZero: iter(frames),
        Onsets=lambda: lambda flux, weights: [0.5],
        RMS=lambda: lambda window: 0.25,
        Loudness=lambda: lambda frame: 0.5,
        Envelope=lambda: lambda frame: [0.1, 0.2],
        SpectralPeaks=lambda sampleRate: lambda spectrum: (np.array([440.0]), np.array([1.0])),
        HPCP=lambda **kwargs: lambda frequencies, magnitudes: np.zeros(12, dtype=np.float32),
        Spectrum=lambda size: lambda frame: frame,
        MelBands=lambda numberBands, sampleRate, inputSize: lambda spectrum: np.zeros(numberBands, dtype=np.float32),
        Centroid=lambda: lambda spectrum: 0.75,
    )

    plot_calls: list[str] = []
    events: list[dict] = []

    monkeypatch.setattr(essentia_module, "es", fake_es)
    monkeypatch.setattr(
        essentia_module,
        "extract_rhythm_descriptors",
        lambda audio: {
            "beats_position": [0.0, 0.5],
            "bpm_intervals": [0.5, 0.5],
            "bpm": 120.0,
            "confidence": 0.9,
        },
    )
    monkeypatch.setattr(essentia_module, "plot_essentia_analysis", lambda *args: plot_calls.append("rhythm"))
    monkeypatch.setattr(essentia_module, "plot_loudness_envelope", lambda *args: plot_calls.append("loudness_envelope"))
    monkeypatch.setattr(essentia_module, "plot_chroma_hpcp", lambda *args: plot_calls.append("chroma_hpcp"))
    monkeypatch.setattr(essentia_module, "plot_mel_bands", lambda *args: plot_calls.append("mel_bands"))
    monkeypatch.setattr(essentia_module, "plot_spectral_centroid", lambda *args: plot_calls.append("spectral_centroid"))

    artifacts = essentia_module.analyze_with_essentia(
        audio_path=str(tmp_path / "song.wav"),
        out_dir=str(tmp_path),
        part_name="mix",
        progress_callback=events.append,
    )

    expected_stages = [
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
    ]

    assert [event["stage"] for event in events] == expected_stages
    assert [event["step_current"] for event in events] == list(range(1, len(expected_stages) + 1))
    assert {event["step_total"] for event in events} == {len(expected_stages)}
    assert {event["part_name"] for event in events} == {"mix"}
    assert events[5]["message"] == "essentia-analysis [6/15] Loudness & Envelope"
    assert set(artifacts) == {"rhythm", "loudness_envelope", "chroma_hpcp", "mel_bands", "spectral_centroid"}
    assert plot_calls == []


def test_analyze_with_essentia_can_emit_plot_stages_when_enabled(tmp_path: Path, monkeypatch) -> None:
    frames = [np.array([0.1, 0.2], dtype=np.float32), np.array([0.2, 0.3], dtype=np.float32)]

    fake_es = SimpleNamespace(
        AudioLoader=lambda filename: lambda: (np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32), 2),
        KeyExtractor=lambda: lambda audio: ("C", "major", 0.8),
        Windowing=lambda type: lambda frame: frame,
        FFT=lambda: lambda frame: frame,
        CartesianToPolar=lambda: lambda fft_complex: (fft_complex, fft_complex),
        OnsetDetection=lambda method: lambda magnitude, phase: 1.0,
        FrameGenerator=lambda audio, frameSize, hopSize, startFromZero: iter(frames),
        Onsets=lambda: lambda flux, weights: [0.5],
        RMS=lambda: lambda window: 0.25,
        Loudness=lambda: lambda frame: 0.5,
        Envelope=lambda: lambda frame: [0.1, 0.2],
        SpectralPeaks=lambda sampleRate: lambda spectrum: (np.array([440.0]), np.array([1.0])),
        HPCP=lambda **kwargs: lambda frequencies, magnitudes: np.zeros(12, dtype=np.float32),
        Spectrum=lambda size: lambda frame: frame,
        MelBands=lambda numberBands, sampleRate, inputSize: lambda spectrum: np.zeros(numberBands, dtype=np.float32),
        Centroid=lambda: lambda spectrum: 0.75,
    )

    plot_calls: list[str] = []
    events: list[dict] = []

    monkeypatch.setattr(essentia_module, "es", fake_es)
    monkeypatch.setattr(
        essentia_module,
        "extract_rhythm_descriptors",
        lambda audio: {
            "beats_position": [0.0, 0.5],
            "bpm_intervals": [0.5, 0.5],
            "bpm": 120.0,
            "confidence": 0.9,
        },
    )
    monkeypatch.setattr(essentia_module, "plot_essentia_analysis", lambda *args: plot_calls.append("rhythm"))
    monkeypatch.setattr(essentia_module, "plot_loudness_envelope", lambda *args: plot_calls.append("loudness_envelope"))
    monkeypatch.setattr(essentia_module, "plot_chroma_hpcp", lambda *args: plot_calls.append("chroma_hpcp"))
    monkeypatch.setattr(essentia_module, "plot_mel_bands", lambda *args: plot_calls.append("mel_bands"))
    monkeypatch.setattr(essentia_module, "plot_spectral_centroid", lambda *args: plot_calls.append("spectral_centroid"))

    essentia_module.analyze_with_essentia(
        audio_path=str(tmp_path / "song.wav"),
        out_dir=str(tmp_path),
        part_name="mix",
        generate_plots=True,
        progress_callback=events.append,
    )

    assert events[-1]["stage"] == "Plot Spectral Centroid"
    assert events[-1]["step_total"] == 20
    assert plot_calls == ["rhythm", "loudness_envelope", "chroma_hpcp", "mel_bands", "spectral_centroid"]