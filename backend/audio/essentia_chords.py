import essentia
import essentia.standard as es
import json
from pathlib import Path
import numpy as np

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

NOTE_FREQS = {
    "C2": 65.41,
    "C4": 261.63,
}

def extract_chords_and_align(audio_path: str):
    loader = es.MonoLoader(filename=audio_path)
    audio = loader()

    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    bpm, beats, _, _, _ = rhythm_extractor(audio)
    beats = [float(b) for b in beats]

    windowing = es.Windowing(type='hann')
    spectrum = es.Spectrum()
    spectral_peaks = es.SpectralPeaks()
    hpcp_full = es.HPCP(size=12)
    hpcp_high = es.HPCP(size=12)
    hpcp_low = es.HPCP(size=12)

    frame_size = 4096
    hop_size = 2048
    sample_rate = 44100

    last_chord = None
    chord_events = []

    for i, frame in enumerate(es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True)):
        timestamp = i * hop_size / sample_rate
        spec = spectrum(windowing(frame))
        freqs, mags = spectral_peaks(spec)

        # Split by musical range (C2 to C4)
        bass_freqs = [f for f in freqs if NOTE_FREQS["C2"] <= f <= NOTE_FREQS["C4"]]
        bass_mags = [m for f, m in zip(freqs, mags) if NOTE_FREQS["C2"] <= f <= NOTE_FREQS["C4"]]
        upper_freqs = [f for f in freqs if f > NOTE_FREQS["C4"]]
        upper_mags = [m for f, m in zip(freqs, mags) if f > NOTE_FREQS["C4"]]

        bass_hpcp = hpcp_low(np.array(bass_freqs), np.array(bass_mags))
        upper_hpcp = hpcp_high(np.array(upper_freqs), np.array(upper_mags))

        chord, confidence = estimate_chord(bass_hpcp)
        melody, mel_conf = estimate_chord(upper_hpcp)

        if chord and chord != last_chord:
            last_chord = chord
            nearest_beat = min(beats, key=lambda b: abs(b - timestamp)) if beats else None
            aligned_beat = max([b for b in beats if b <= timestamp], default=None)
            chord_events.append({
                "chord": chord,
                "confidence": confidence,
                "melody_hint": melody,
                "melody_conf": mel_conf,
                "time": round(timestamp, 3),
                "nearest_time": round(nearest_beat, 3) if nearest_beat is not None else None,
                "aligned_time": round(aligned_beat, 3) if aligned_beat is not None else None
            })

    result = {
        "bpm": round(bpm, 2),
        "beats": [round(b, 3) for b in beats],
        "chords": chord_events
    }

    output_json_path = f"{audio_path}.chords.json"
    with open(output_json_path, 'w') as f:
        json.dump(result, f, indent=4)

    return result

if __name__ == "__main__":
    LOCAL_TEST_SONG_PATH = "/home/darkangel/ai-light-show/songs/Gabry Ponte - Tutta LItalia.mp3"
    extract_chords_and_align(LOCAL_TEST_SONG_PATH)
