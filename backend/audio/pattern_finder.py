## Technical Debt:
## get_stem_clusters is not producing expected results:
## - The sample song contains 7 distinct drum patterns, but the clustering is not identifying them.
## - This may be due to the feature extraction or clustering method used.
## - Consider using more robust clustering methods or feature extraction techniques.
## - Validate clustering results and adjust parameters if needed 

import librosa
import numpy as np
from pathlib import Path
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from collections import Counter
import scipy.signal
from ..models.song_metadata import ensure_json_serializable

def get_stem_clusters(
    beats,
    stem_file,
    full_file=None,
    n_mels=64,
    fmax=8000,
    hop_length=512,
    debug=False
):
    """ 
    Find patterns in the stem audio file:
    - Create a list of unique patterns.
    - Create a timeline of clusters (start_time, cluster_label).
    - Cluster_label "0" is reserved for silence or no pattern.
    :return: Dictionary containing cluster labels, segments, and other analysis results.
    """
    print(f"⛓️ Analyzing stem clusters")

    if not Path(stem_file).exists():
        raise FileNotFoundError(f"Stem file not found: {stem_file}")
        
    y, sr = librosa.load(stem_file, sr=None)
    if len(y) == 0:
        raise ValueError("Audio file is empty or could not be loaded")

    # Check if entire audio is silent
    if np.allclose(y, 0, atol=1e-4):
        return {
            "clusters_timeline": [],
            "n_clusters": 0,
            "clusterization_score": 0.0,
            "best_duration_beats": 0,
            "all_durations": {}
        }

    # Use shorter segments for better pattern discrimination (2-4 beats)
    segment_length_beats = 2  # Use 2-beat segments for finer pattern detection
    avg_beat_duration = np.mean(np.diff(beats)) if len(beats) > 1 else 0.5
    segment_duration = segment_length_beats * avg_beat_duration
    
    print(f"Using {segment_length_beats}-beat segments (~{segment_duration:.2f}s each)")
    
    # Create segments with slight overlap for better pattern boundaries
    segment_times = []
    segment_features = []
    
    # Start from first beat and create overlapping windows
    current_time = beats[0] if len(beats) > 0 else 0
    end_time = beats[-1] if len(beats) > 0 else librosa.frames_to_time(len(y), sr=sr)
    
    hop_time = segment_duration * 0.5  # 50% overlap for better boundary detection
    
    # Calculate total segments for progress indicator
    total_segments = int((end_time - current_time - segment_duration) / hop_time) + 1
    if debug:
        print(f"🔄 Processing {total_segments} segments...")
    
    segment_count = 0
    while current_time + segment_duration <= end_time:
        segment_count += 1
        if debug and segment_count % 20 == 0:
            print(f"  Processed {segment_count}/{total_segments} segments ({segment_count/total_segments*100:.1f}%)")
            
        start_time = current_time
        end_time_seg = current_time + segment_duration
        
        start_sample = int(start_time * sr)
        end_sample = int(end_time_seg * sr)
        
        if end_sample > len(y):
            end_sample = len(y)
        if start_sample >= end_sample:
            current_time += hop_time
            continue
            
        segment_audio = y[start_sample:end_sample]
        
        # Handle silent segments differently - still include them but mark them
        max_amplitude = np.max(np.abs(segment_audio))
        if max_amplitude < 1e-4:
            # Silent segment - use zero features
            features = np.zeros(12)  # Match the feature count below
        else:
            # Extract enhanced features for better discrimination
            # 1. MFCCs for timbral characteristics
            segment_mfcc = librosa.feature.mfcc(y=segment_audio, sr=sr, n_mfcc=8, 
                                               n_mels=32, fmax=fmax)
            mfcc_mean = np.mean(segment_mfcc, axis=1)
            
            # 2. Spectral features for drum type discrimination
            spectral_centroids = librosa.feature.spectral_centroid(y=segment_audio, sr=sr)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=segment_audio, sr=sr, roll_percent=0.85)
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=segment_audio, sr=sr)
            
            # 3. Energy and dynamics
            rms_energy = librosa.feature.rms(y=segment_audio)
            
            # 4. Zero crossing rate for percussive content
            zcr = librosa.feature.zero_crossing_rate(segment_audio)
            
            # Combine features with more discrimination
            features = np.concatenate([
                mfcc_mean,  # 8 features
                [float(np.mean(spectral_centroids))],    # 1 feature
                [float(np.mean(spectral_rolloff))],      # 1 feature  
                [float(np.mean(spectral_bandwidth))],    # 1 feature
                [float(np.mean(rms_energy))]             # 1 feature
            ])  # Total: 12 features
        
        segment_features.append(features)
        segment_times.append((start_time, end_time_seg))
        
        current_time += hop_time

    if debug:
        print(f"✅ Extracted features from {len(segment_features)} segments")

    if len(segment_features) < 2:
        return {
            "clusters_timeline": [],
            "n_clusters": 0,
            "clusterization_score": 0.0,
            "best_duration_beats": 0,
            "all_durations": {}
        }

    # Normalize features
    X = StandardScaler().fit_transform(np.array(segment_features))
    
    if debug:
        print("🔍 Finding optimal clustering...")
    
    # Try multiple clustering approaches and pick the best one
    best_labels = None
    best_score = -1
    best_n_clusters = 0
    
    # Try different numbers of clusters with K-means for more stable results
    from sklearn.cluster import KMeans
    for n_clusters in range(3, min(15, len(segment_features))):  # Start at 3 to catch more patterns
        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            
            if len(set(labels)) > 1:
                try:
                    score = silhouette_score(X, labels)
                    if score > best_score:
                        best_score = score
                        best_labels = labels
                        best_n_clusters = n_clusters
                except:
                    pass
        except:
            pass
    
    # Also try Agglomerative clustering with more sensitive thresholds
    for threshold in [0.5, 1.0, 1.5, 2.0, 3.0]:  # More sensitive thresholds
        try:
            clustering = AgglomerativeClustering(n_clusters=None, 
                                               distance_threshold=threshold, 
                                               linkage='ward')
            labels = clustering.fit_predict(X)
            n_clusters = clustering.n_clusters_
            
            if 3 <= n_clusters <= 15:  # Allow more clusters to catch finer patterns
                try:
                    score = silhouette_score(X, labels)
                    if score > best_score:
                        best_score = score
                        best_labels = labels
                        best_n_clusters = n_clusters
                except:
                    pass
        except:
            pass
    
    # Fallback to simple threshold if no good clustering found
    if best_labels is None:
        clustering = AgglomerativeClustering(n_clusters=None, 
                                           distance_threshold=1.5,  # More sensitive threshold
                                           linkage='ward')
        best_labels = clustering.fit_predict(X)
        best_n_clusters = clustering.n_clusters_
        best_score = 0.0

    if debug:
        print(f"📊 Clustering complete: {best_n_clusters} clusters found")

    # Create timeline with pattern starts
    clusters_timeline = []
    for i, (label, (start_time, end_time)) in enumerate(zip(best_labels, segment_times)):
        # Skip noise points from DBSCAN (not applicable now but keeping for safety)
        if label == -1:
            continue
            
        clusters_timeline.append({
            "start": float(start_time),
            "end": float(end_time),
            "cluster": int(label) + 1  # Adding 1 to reserve 0 for silence
        })
    
    # Post-process: merge very short consecutive segments of the same cluster
    merged_timeline = []
    if clusters_timeline:
        if debug:
            print("🔧 Post-processing: merging similar adjacent segments...")
            
        current_segment = clusters_timeline[0]
        
        for i in range(1, len(clusters_timeline)):
            next_segment = clusters_timeline[i]
            
            # If same cluster and gap is small (< 2.0 seconds), merge them
            if (current_segment['cluster'] == next_segment['cluster'] and 
                next_segment['start'] - current_segment['end'] < 2.0):
                current_segment['end'] = next_segment['end']
            else:
                merged_timeline.append(current_segment)
                current_segment = next_segment
        
        merged_timeline.append(current_segment)
    
    if debug:
        print(f"Found {best_n_clusters} clusters with score {best_score:.3f}")
        print(f"Generated {len(clusters_timeline)} segments")
        cluster_counts = Counter([c['cluster'] for c in clusters_timeline])
        print(f"Cluster distribution: {dict(cluster_counts)}")
        
        # Show timeline for comparison with expected patterns
        print("\n🎵 Pattern Timeline:")
        for segment in merged_timeline:
            duration = segment['end'] - segment['start']
            print(f"  {segment['start']:.1f}s - {segment['end']:.1f}s: [Cluster {segment['cluster']}] ({duration:.1f}s)")
        
        print("\n📋 Expected patterns for comparison:")
        print("  0.0s - 34.2s: [0] drum is silent (intro)")
        print("  34.2s - 55.2s: [1] first kick")
        print("  55.2s - 81.2s: [2] a tom is added")
        print("  81.2s - 97.1s: [3] tom change pattern")
        print("  97.1s - 117.1s: [4] a tom+hihat pattern")
        print("  102.3s - 120s: [5] a two kicks then two snares pattern")
        print("  120.3s - 122s: [6] snare only pattern")
        print("  122s - 130s: [4] a tom+hihat pattern")

    # Output schema for other functions
    return ensure_json_serializable({
        "cluster_labels": list(np.unique(best_labels[best_labels != -1])) if best_labels is not None else [],
        "segments": merged_timeline, 
        "n_clusters": best_n_clusters,
        "clusterization_score": float(best_score),
        "clusters_timeline": clusters_timeline
    })

if __name__ == "__main__":
    import sys
    import os
    
    # Add the project root to the path
    project_root = "/home/darkangel/ai-light-show"
    sys.path.insert(0, project_root)
    
    try:
        # load the song metadata
        from backend.models.song_metadata import SongMetadata
        print("Loading song metadata...")
        song = SongMetadata("born_slippy", songs_folder="/home/darkangel/ai-light-show/songs")
        print("Song metadata loaded.")
        beats = song.get_beats_array()
        print(f"Beats loaded: {len(beats)} beats found.")
        
        if len(beats) == 0:
            print("ERROR: No beats found in song metadata")
            sys.exit(1)
            
        stem_file = f"/home/darkangel/ai-light-show/songs/temp/htdemucs/{song.song_name}/drums.wav"
        print(f"Stem file: {stem_file}")
        
        if not os.path.exists(stem_file):
            print(f"ERROR: Stem file not found: {stem_file}")
            sys.exit(1)

        stem_clusters = get_stem_clusters(
            beats,
            stem_file,
            debug=True
        )
        
        # Save patterns to song metadata
        if isinstance(stem_clusters, dict) and 'clusters_timeline' in stem_clusters:
            timeline = stem_clusters['clusters_timeline']
            if isinstance(timeline, list) and len(timeline) > 0:
                # Clear existing patterns and add new ones
                song.clear_patterns()
                song.add_patterns("drums", timeline)
                song.save()
                print(f"\n💾 Saved {len(timeline)} drum pattern segments to song metadata")
            else:
                print("\n⚠️  No patterns found to save")
        else:
            print("\n❌ Invalid clustering results, cannot save patterns")
        
        # print("--- RESULTS ---")
        # import json
        # print(json.dumps(stem_clusters, indent=2))
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()



