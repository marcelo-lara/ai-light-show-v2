from __future__ import annotations

import numpy as np


def build_window_metrics(audio: np.ndarray, sample_rate: int) -> list[dict[str, float | str]]:
    window_size = max(int(sample_rate * 0.5), 1)
    hop_size = max(int(sample_rate * 0.25), 1)
    last_start = max(audio.shape[1] - window_size, 0)
    starts = list(range(0, last_start + 1, hop_size)) or [0]
    if starts[-1] != last_start:
        starts.append(last_start)
    metrics: list[dict[str, float | str]] = []
    previous_energy = 0.0
    for start in starts:
        end = min(start + window_size, audio.shape[1])
        left = audio[0, start:end]
        right = audio[1, start:end]
        left_rms = _rms(left)
        right_rms = _rms(right)
        total = max((left_rms + right_rms) / 2.0, 1e-6)
        balance = (left_rms - right_rms) / (left_rms + right_rms + 1e-6)
        corr = _corr(left, right)
        left_focus = _band_focus(left, sample_rate)
        right_focus = _band_focus(right, sample_rate)
        band_balances = _band_balances(left, right, sample_rate)
        metrics.append(
            {
                "start_s": start / sample_rate,
                "end_s": end / sample_rate,
                "energy": total,
                "balance": balance,
                "corr": corr,
                "left_transient": _transient_score(left, left_rms),
                "right_transient": _transient_score(right, right_rms),
                "decay": max(previous_energy - total, 0.0),
                "left_focus": left_focus,
                "right_focus": right_focus,
                **band_balances,
            }
        )
        previous_energy = total
    return metrics


def _rms(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(values), dtype=np.float64) + 1e-12))


def _transient_score(values: np.ndarray, rms_value: float) -> float:
    if values.size < 2:
        return 0.0
    diff_energy = np.sqrt(np.mean(np.square(np.diff(values)), dtype=np.float64) + 1e-12)
    return float(diff_energy / (rms_value + 1e-6))


def _corr(left: np.ndarray, right: np.ndarray) -> float:
    if left.size < 2 or np.std(left) < 1e-8 or np.std(right) < 1e-8:
        return 1.0
    return float(np.clip(np.corrcoef(left, right)[0, 1], -1.0, 1.0))


def _band_focus(values: np.ndarray, sample_rate: int) -> str:
    if values.size < 8:
        return "broad"
    spectrum = np.abs(np.fft.rfft(values * np.hanning(values.size))) ** 2
    freqs = np.fft.rfftfreq(values.size, d=1.0 / sample_rate)
    low = float(np.sum(spectrum[(freqs >= 20) & (freqs < 200)]))
    mid = float(np.sum(spectrum[(freqs >= 200) & (freqs < 2000)]))
    high = float(np.sum(spectrum[freqs >= 2000]))
    total = max(low + mid + high, 1e-6)
    band, value = max({"low": low, "mid": mid, "high": high}.items(), key=lambda item: item[1])
    return band if value / total >= 0.5 else "broad"


def _band_balances(left: np.ndarray, right: np.ndarray, sample_rate: int) -> dict[str, float]:
    if left.size < 8 or right.size < 8:
        return {"low_balance": 0.0, "mid_balance": 0.0, "high_balance": 0.0}
    left_spectrum = np.abs(np.fft.rfft(left * np.hanning(left.size))) ** 2
    right_spectrum = np.abs(np.fft.rfft(right * np.hanning(right.size))) ** 2
    freqs = np.fft.rfftfreq(left.size, d=1.0 / sample_rate)
    return {
        "low_balance": _balance_for_band(left_spectrum, right_spectrum, (freqs >= 20) & (freqs < 200)),
        "mid_balance": _balance_for_band(left_spectrum, right_spectrum, (freqs >= 200) & (freqs < 2000)),
        "high_balance": _balance_for_band(left_spectrum, right_spectrum, freqs >= 2000),
    }


def _balance_for_band(left_spectrum: np.ndarray, right_spectrum: np.ndarray, mask: np.ndarray) -> float:
    left_value = float(np.sum(left_spectrum[mask]))
    right_value = float(np.sum(right_spectrum[mask]))
    return float((left_value - right_value) / (left_value + right_value + 1e-9))