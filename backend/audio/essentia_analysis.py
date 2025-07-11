import essentia
import essentia.standard as es
import json
from pathlib import Path
from sklearn.cluster import KMeans
import numpy as np
import math
from collections import Counter

CHORD_TEMPLATES = {
    "C":     [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    "C#":    [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],
    "D":     [0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0],
    "D#":    [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
    "E":     [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
    "F":     [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
    "F#":    [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0],
    "G":     [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],
    "G#":    [1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
    "A":     [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
    "A#":    [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0],
    "B":     [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1],
}

COMMON_PROGRESSIONS = {
    ("C", "G", "Am", "F"): "I-V-vi-IV",
    ("C", "F", "G", "C"): "I-IV-V-I",
    ("C", "Am", "F", "G"): "I-vi-IV-V",
    ("C", "F", "Am", "G"): "I-IV-vi-V",
    ("C", "Am", "Dm", "G"): "I-vi-ii-V",
}

def estimate_chord(hpcp_vector, threshold=0.85):
    def cosine_similarity(a, b):
        a, b = np.array(a), np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    best_chord = None
    best_score = 0.0
    for chord, template in CHORD_TEMPLATES.items():
        score = cosine_similarity(hpcp_vector, template)
        if score > best_score:
            best_score = score
            best_chord = chord

    if best_score >= threshold:
        return best_chord, round(best_score, 3)
    return None, best_score


def cluster_chord_progressions(regions):
    sequences = []
    labels = []
    for i in range(0, len(regions) - 3):
        progression = tuple(regions[j].get("chord") for j in range(i, i + 4))
        if all(progression):
            sequences.append(progression)
            labels.append(i)

    if not sequences:
        return regions

    unique_progressions = list({seq for seq in sequences})
    progression_map = {prog: chr(65 + idx) for idx, prog in enumerate(unique_progressions)}

    for i, prog in zip(labels, sequences):
        label = progression_map[prog]
        if prog in COMMON_PROGRESSIONS:
            label = COMMON_PROGRESSIONS[prog]
        for j in range(4):
            regions[i + j]["progression_label"] = label

    return regions


def extract_with_essentia(audio_path: str, bars_1=4, bars_2=2):

    print(f"🎧 Extracting beats, volume and basic metadata...")

    # Load audio (mono)
    loader = es.MonoLoader(filename=audio_path)
    audio = loader()

    # --- Compute RMS (volume) for each frame ---
    frame_length = 2048
    hop_length = 512
    rms = es.RMS()
    rms_values = []
    rms_times = []
    for i, frame in enumerate(es.FrameGenerator(audio, frameSize=frame_length, hopSize=hop_length, startFromZero=True)):
        rms_val = float(rms(frame))
        rms_values.append(rms_val)
        rms_times.append((i * hop_length) / 44100.0)

    # Beat detection
    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    bpm, beats, _, _, _ = rhythm_extractor(audio)

    # Interpolate RMS at beat times
    def interpolate_series_at_targets(series_times, series_values, target_times):
        import numpy as np
        return np.interp(target_times, series_times, series_values).tolist()

    beat_volumes = interpolate_series_at_targets(rms_times, rms_values, [float(b) for b in beats])
    beat_volume_tuples = [[round(float(b), 4), round(float(v), 4)] for b, v in zip(beats, beat_volumes)]

    # Load audio (mono)
    loader = es.MonoLoader(filename=audio_path)
    audio = loader()

    # Beat detection
    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    bpm, beats, _, _, _ = rhythm_extractor(audio)

    # Chroma extraction (via HPCP)
    frame_size = 4096
    hop_size = 2048

    windowing = es.Windowing(type='hann')
    spectrum = es.Spectrum()
    spectral_peaks = es.SpectralPeaks()
    hpcp_extractor = es.HPCP(size=12)

    hpcp_time_series = []
    audio_duration = len(audio) / 44100.0
    frame_times = []

    for i, frame in enumerate(es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True)): 
        timestamp = (i * hop_size) / 44100.0
        spec = spectrum(windowing(frame))
        freqs, mags = spectral_peaks(spec)
        hpcp = hpcp_extractor(freqs, mags)
        hpcp_time_series.append([float(h) for h in hpcp])
        frame_times.append(timestamp)

    # Key detection
    key_detector = es.KeyExtractor()
    key, scale, strength = key_detector(audio)

    def get_avg_hpcp(start, end):
        values = [vec for t, vec in zip(frame_times, hpcp_time_series) if start <= t < end]
        if not values:
            return [0.0] * 12
        return [float(sum(col) / len(col)) for col in zip(*values)]

    beats_sec = [float(b) for b in beats]
    song_duration = beats_sec[-1] if beats_sec else audio_duration

    def generate_regions_by_beats(beats, beats_per_region):
        regions = []
        num_beats = len(beats)
        for i in range(0, num_beats, beats_per_region):
            if i + beats_per_region >= num_beats:
                break
            start = beats[i]
            end = beats[i + beats_per_region]
            hpcp = get_avg_hpcp(start, end)
            energy = sum(hpcp)
            chord, confidence = estimate_chord(hpcp)
            region = {
                "start": round(start, 3),
                "end": round(end, 3),
                "hpcp": [round(val, 4) for val in hpcp],
                "energy": round(energy, 4),
            }
            if chord:
                region["chord"] = chord
                region["confidence"] = confidence
            regions.append(region)
        return regions

    def cluster_regions(regions, n_clusters=4):
        X = np.array([r["hpcp"] for r in regions])
        if len(X) < n_clusters:
            return regions
        kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(X)
        for i, r in enumerate(regions):
            r["label"] = chr(65 + kmeans.labels_[i])
        return regions

    regions_4 = cluster_regions(generate_regions_by_beats(beats_sec, bars_1 * 4))
    regions_2 = cluster_regions(generate_regions_by_beats(beats_sec, bars_2 * 4))
    regions_1 = generate_regions_by_beats(beats_sec, 4)
    regions_1 = cluster_chord_progressions(regions_1)

    avg_hpcp = get_avg_hpcp(0.0, song_duration)

    results = {
        "bpm": round(float(bpm), 2),
        "song_duration": float(song_duration),
        "key": key,
        "scale": scale,
        "strength": float(strength),
        "beats": [round(float(b), 4) for b in beats],
        "beat_volumes": beat_volume_tuples,
        "avg_hpcp": [round(float(val), 4) for val in avg_hpcp],
        "regions_4bars": regions_4,
        "regions_2bars": regions_2,
        "regions_1bar": regions_1
    }

    return results


if __name__ == "__main__":
    results = extract_with_essentia("/home/darkangel/ai-light-show/songs/born_slippy.mp3"    )
    Path("/home/darkangel/ai-light-show/songs/born_slippy.mp3.analysis.json").write_text(json.dumps(results, indent=2))
    print(f"✅ Saved beat and chord data")
