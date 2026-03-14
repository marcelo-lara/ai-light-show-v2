from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import matplotlib.pyplot as plt
import numpy as np


TEXT_COLOR = "#E6EDF3"
GRID_COLOR = "#2A2F3A"


def _apply_dark_axes_style(axes: Sequence[plt.Axes]) -> None:
    for axis in axes:
        axis.set_facecolor("none")
        axis.tick_params(colors=TEXT_COLOR)
        axis.xaxis.label.set_color(TEXT_COLOR)
        axis.yaxis.label.set_color(TEXT_COLOR)
        axis.title.set_color(TEXT_COLOR)
        for spine in axis.spines.values():
            spine.set_color(TEXT_COLOR)
        axis.grid(color=GRID_COLOR, alpha=0.35)


def _save_svg_transparent(fig: plt.Figure, svg_path: Path) -> None:
    fig.patch.set_alpha(0)
    plt.savefig(svg_path, format="svg", transparent=True, facecolor="none", edgecolor="none")


def plot_essentia_analysis(
    audio: np.ndarray,
    sr: int,
    beats: np.ndarray,
    downbeats: np.ndarray,
    onset_rate: Sequence[float],
    beat_loudness: List[float],
    svg_path: Path,
):
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

    time = np.linspace(0, len(audio) / sr, len(audio))

    axes[0].plot(time, audio, color="#4DA3FF", alpha=0.8)
    for beat in beats:
        axes[0].axvline(beat, color="#FF5A5F", linestyle="--", alpha=0.65)
    for downbeat in downbeats:
        axes[0].axvline(downbeat, color="#24D17E", linestyle="-", alpha=0.8)
    axes[0].set_title("Waveform with Beats (red) and Downbeats (green)")
    axes[0].set_ylabel("Amplitude")

    onset_time = np.linspace(0, len(audio) / sr, len(onset_rate))
    axes[1].plot(onset_time, onset_rate, color="#F9A826")
    axes[1].set_title("Onset Rate")
    axes[1].set_ylabel("Rate")

    beat_times = beats[: len(beat_loudness)]
    axes[2].bar(beat_times, beat_loudness, width=0.1, color="#B388FF", alpha=0.8)
    axes[2].set_title("Beat Loudness")
    axes[2].set_ylabel("Loudness")
    axes[2].set_xlabel("Time (s)")
    _apply_dark_axes_style(axes)

    plt.tight_layout()
    _save_svg_transparent(fig, svg_path)
    plt.close()


def plot_loudness_envelope(times: List[float], loudness: List[float], envelope: List[float], svg_path: Path):
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    axes[0].plot(times, loudness, color="#4DA3FF")
    axes[0].set_title("Loudness")
    axes[0].set_ylabel("Loudness")

    axes[1].plot(times, envelope, color="#FF5A5F")
    axes[1].set_title("Envelope")
    axes[1].set_ylabel("Envelope")
    axes[1].set_xlabel("Time (s)")
    _apply_dark_axes_style(axes)

    plt.tight_layout()
    _save_svg_transparent(fig, svg_path)
    plt.close()


def plot_chroma_hpcp(times: List[float], hpcp: List[List[float]], svg_path: Path):
    import matplotlib.cm as cm

    hpcp_array = np.array(hpcp)
    fig, ax = plt.subplots(figsize=(12, 6))

    cax = ax.imshow(hpcp_array.T, aspect='auto', origin='lower', extent=[times[0], times[-1], 0, 12], cmap=cm.viridis)
    ax.set_title("Chroma HPCP")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Chroma Bin")
    colorbar = fig.colorbar(cax, ax=ax, label="Magnitude")
    _apply_dark_axes_style((ax,))
    colorbar.ax.tick_params(colors=TEXT_COLOR)
    colorbar.ax.yaxis.label.set_color(TEXT_COLOR)
    colorbar.outline.set_edgecolor(TEXT_COLOR)

    plt.tight_layout()
    _save_svg_transparent(fig, svg_path)
    plt.close()


def plot_mel_bands(times: List[float], mel_bands: List[List[float]], svg_path: Path):
    import matplotlib.cm as cm

    mel_array = np.array(mel_bands)
    fig, ax = plt.subplots(figsize=(12, 6))

    cax = ax.imshow(mel_array.T, aspect='auto', origin='lower', extent=[times[0], times[-1], 0, 40], cmap=cm.plasma)
    ax.set_title("Mel-Frequency Bands")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Mel Band")
    colorbar = fig.colorbar(cax, ax=ax, label="Magnitude")
    _apply_dark_axes_style((ax,))
    colorbar.ax.tick_params(colors=TEXT_COLOR)
    colorbar.ax.yaxis.label.set_color(TEXT_COLOR)
    colorbar.outline.set_edgecolor(TEXT_COLOR)

    plt.tight_layout()
    _save_svg_transparent(fig, svg_path)
    plt.close()


def plot_spectral_centroid(times: List[float], centroid: List[float], svg_path: Path):
    fig, ax = plt.subplots(figsize=(12, 4))

    ax.plot(times, centroid, color="#24D17E")
    ax.set_title("Spectral Centroid")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Centroid (Hz)")
    _apply_dark_axes_style((ax,))

    plt.tight_layout()
    _save_svg_transparent(fig, svg_path)
    plt.close()
