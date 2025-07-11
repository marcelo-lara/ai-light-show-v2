import torch
import torchaudio
import numpy as np
from transformers import Wav2Vec2Processor, Wav2Vec2Model, AutoConfig
from pathlib import Path
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from collections import Counter
import soundfile as sf

# Global variables for lazy loading
_model = None
_processor = None
_device = None

def get_model_and_processor():
    """Lazy load the model and processor only when needed"""
    global _model, _processor, _device
    
    if _model is None or _processor is None:
        print("Loading Wav2Vec2 model (this may take a while on first run)...")
        model_name_or_path = "ALM/wav2vec2-large-audioset"
        
        try:
            _processor = Wav2Vec2Processor.from_pretrained(model_name_or_path)
            _model = Wav2Vec2Model.from_pretrained(model_name_or_path)
            
            _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            _model = _model.to(_device)
            _model.eval()
            print(f"Model loaded successfully on {_device}")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Falling back to simpler model...")
            # Fallback to a smaller, more reliable model
            model_name_or_path = "facebook/wav2vec2-base-960h"
            try:
                _processor = Wav2Vec2Processor.from_pretrained(model_name_or_path)
                _model = Wav2Vec2Model.from_pretrained(model_name_or_path)
                _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                _model = _model.to(_device)
                _model.eval()
                print(f"Fallback model loaded successfully on {_device}")
            except Exception as e2:
                print(f"Error loading fallback model: {e2}")
                raise RuntimeError(f"Failed to load any Wav2Vec2 model. Original error: {e}, Fallback error: {e2}")
    
    return _model, _processor, _device

def extract_wav2vec2_embedding(audio_array, sr):
    try:
        model, processor, device = get_model_and_processor()
        
        if sr != 16000:
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
            audio_array = resampler(torch.tensor(audio_array))
        else:
            audio_array = torch.tensor(audio_array)

        input_values = processor(audio_array.squeeze().numpy(), sampling_rate=16000, return_tensors="pt").input_values
        with torch.no_grad():
            outputs = model(input_values.to(device))
            last_hidden_state = outputs.last_hidden_state
        return torch.mean(last_hidden_state, dim=1).squeeze().cpu().numpy()
    except Exception as e:
        print(f"Error extracting embedding: {e}")
        # Return zero embedding on error
        return np.zeros(768)  # Default embedding size

def get_stem_clusters_with_model(beats, stem_file, min_duration_beats=1, debug=False):
    # Input validation
    if len(beats) < min_duration_beats + 1:
        raise ValueError(f"Not enough beats ({len(beats)}) for minimum segment duration ({min_duration_beats})")
    
    if not Path(stem_file).exists():
        raise FileNotFoundError(f"Stem file not found: {stem_file}")
    
    print(f" .. Analyzing clusters of {stem_file}")
    
    try:
        y, sr = torchaudio.load(stem_file)
        y = y.mean(dim=0).numpy()  # Convert to mono
    except Exception as e:
        print(f"Error loading audio file: {e}")
        raise

    # Create beat-aligned segments
    segments = []
    for i in range(len(beats) - min_duration_beats):
        start_time = float(beats[i])
        end_time = float(beats[i + min_duration_beats])
        segments.append((start_time, end_time))

    segment_features = []
    silence_indices = []
    for idx, (start, end) in enumerate(segments):
        start_sample = int(start * sr)
        end_sample = int(end * sr)
        segment_audio = y[start_sample:end_sample]

        if np.allclose(segment_audio, 0, atol=1e-4):
            silence_indices.append(idx)
            segment_features.append(np.zeros(768))  # size of wav2vec2 embedding
            continue

        embedding = extract_wav2vec2_embedding(segment_audio, sr)
        segment_features.append(embedding)

    X = np.array(segment_features)
    
    # Handle edge cases for clustering
    if X.shape[0] <= 1:
        # Not enough samples for clustering, return single cluster
        cluster_labels = [0] * len(segments)
        n_clusters = 1
    else:
        X = StandardScaler().fit_transform(X)

        clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=15.0, linkage='ward')
        raw_labels = clustering.fit_predict(X)

        # Silence as cluster 0
        cluster_labels = raw_labels.copy()
        for idx in silence_indices:
            cluster_labels[idx] = 0

        # Re-map labels (0 = silence, 1 = most common, 2 = next, ...)
        label_counts = Counter(cluster_labels)
        non_silence = [l for l in label_counts if l != 0]
        sorted_labels = sorted(non_silence, key=lambda l: -label_counts[l])
        remap = {0: 0}
        for new_id, old_id in enumerate(sorted_labels, start=1):
            remap[old_id] = new_id
        cluster_labels = [remap[l] for l in cluster_labels]

        n_clusters = len(set(cluster_labels))

    segment_times_by_cluster = {}
    for i, label in enumerate(cluster_labels):
        segment_times_by_cluster.setdefault(int(label), []).append(segments[i])

    # Optional: save debug audio
    if debug:
        output_base = Path(stem_file).with_suffix("")
        exported = set()
        print("\nCluster Distribution:")
        total = sum(Counter(cluster_labels).values())
        for label, count in sorted(Counter(cluster_labels).items()):
            bar = '█' * int((count / total) * 50)
            print(f"Cluster {label:2d}: {count:3d} segments | {bar}")

        for i, label in enumerate(cluster_labels):
            if label in exported:
                continue
            exported.add(label)
            start, end = segments[i]
            start_sample = int(start * sr)
            end_sample = int(end * sr)
            segment_audio = y[start_sample:end_sample]
            temp_wav = output_base.parent / f"{output_base.stem}_cluster{label}.wav"
            sf.write(temp_wav, segment_audio, sr)

    return {
        "cluster_labels": cluster_labels,
        "segments": segments,
        "n_clusters": n_clusters,
        "cluster_counts": dict(Counter(cluster_labels)),
        "segment_times_by_cluster": segment_times_by_cluster,
        "clusters_timeline": [
            {
                "start": float(start),
                "end": float(end),
                "cluster": int(cluster)
            }
            for (start, end), cluster in sorted(zip(segments, cluster_labels), key=lambda x: x[0][0])
        ]
    }

## Example usage:
if __name__ == "__main__":

    # get base parameters
    from backend.song_metadata import SongMetadata
    song = SongMetadata("born_slippy", songs_folder="/home/darkangel/ai-light-show/songs")

    stem_file = f"/home/darkangel/ai-light-show/songs/temp/htdemucs/{song.song_name}/drums.wav"
    print(f" analyzing {stem_file}...")

    stem_clusters = get_stem_clusters_with_model(
        song.get_beats_array(), 
        stem_file, 
        debug=True
        )

    song.add_patterns("drums_m", stem_clusters['clusters_timeline'])

    print(f"  Found {stem_clusters['n_clusters']} clusters in {len(stem_clusters['clusters_timeline'])} segments for drums...")