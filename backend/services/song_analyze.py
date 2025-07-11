from backend.models.song_metadata import SongMetadata, Section
from backend.audio.pattern_finder_ml import get_stem_clusters_with_model
from backend.audio.arrangement_guess import guess_arrangement
from backend.audio.essentia_analysis import extract_with_essentia
from backend.audio.drums_infer import infer_drums
from backend.audio.demucs_split import extract_stems
from backend.audio.pattern_finder import get_stem_clusters
from backend.audio.audio_proccess import noise_gate

def song_analyze(song: SongMetadata, reset_file: bool = True, debug: bool = False) -> SongMetadata:

    """
    Analyze a song and extract its metadata, beats, BPM, and patterns.
    This function uses Essentia for core analysis and Demucs for stem extraction.
    :param song: SongMetadata object containing the song to analyze.
    :param reset_file: If True, will re-create entire metadata.
    :return: Updated SongMetadata object with analysis results.
    """

    analyze_patterns_using_model = False
    infer_drums_using_model = False
    noise_gate_stems = True


    print(f"🔍 Analyzing song: {song.title} ({song.mp3_path})")

    if reset_file:
        song = SongMetadata(song.song_name, songs_folder=song.songs_folder, ignore_existing=True)

    ## Core analysis using Essentia
    essentia_core = extract_with_essentia(song.mp3_path)
    song.clear_beats()
    song.bpm = essentia_core['bpm']
    song.duration = essentia_core['song_duration']
    [song.add_beat(b) for b in essentia_core['beats']]
    song.set_beats_volume(essentia_core['beat_volumes'])

    ## split song into stems
    stems_folder = extract_stems(song.mp3_path)
    
    if not stems_folder or 'output_folder' not in stems_folder:
        raise ValueError("Failed to extract stems - no output folder returned")

    # analyze stems
    stems_list = ['drums', 'bass']
    song.clear_patterns()

    for stem in stems_list:
        stem_path = f"{stems_folder['output_folder']}/{stem}.wav"

        # apply noise gate to stem
        if noise_gate_stems:
            noise_gate(input_path=stem_path, threshold_db=-35.0)

        # get clusters (librosa)
        try:
            stem_clusters = get_stem_clusters(
                song.get_beats_array(),
                stem_path,
                debug=debug
            )
            if not stem_clusters:
                continue
            
            if 'clusters_timeline' in stem_clusters:
                print(f"  Adding {stem_clusters.get('n_clusters', 0)} clusters for {stem} → Score: {stem_clusters.get('clusterization_score', 0.0):.4f}...")
                song.add_patterns(stem, stem_clusters['clusters_timeline'])
            else:
                print(f"⚠️ No clusters timeline found for {stem}")

        except Exception as e:
            print(f"⚠️ Failed to process {stem}: {str(e)}")
            continue

        # get clusters (ML)
        if analyze_patterns_using_model:
            stem_clusters = get_stem_clusters_with_model(
                song.get_beats_array(), 
                stem_path
            )
            song.add_patterns(f"{stem}_m", stem_clusters['clusters_timeline'])

        ## infer drums
        if infer_drums_using_model and stem == 'drums':
            song.drums = infer_drums(stem_path)

    if song.placeholder_prop:
        guess_arrangement(song)

    return song

def build_test_cues(song: SongMetadata) -> list:
    """
    Build cues for all beats in the song.
    A flash preset is assigned cycling through fixtures.
    The start_brightness is set proportional to the beat volume.
    """
    fixtures_id = ["parcan_pl", "parcan_pr", "parcan_l", "parcan_r"]
    cues = []
    current_fixture = 0
    for beat in (song.beats or []):
        cues.append(add_flash_preset(
            start_time=beat.get("time", 0.0),
            fixture=fixtures_id[current_fixture],
            start_brightness=beat.get("volume", 0.5)
        ))
        current_fixture += 1
        if current_fixture >= len(fixtures_id):
            current_fixture = 0
    return cues

def add_flash_preset(start_time:float=0.0, fixture:str="parcan_l", start_brightness:float=1.0) -> dict:
    """
    Returns a dictionary of fixture presets.
    This is a placeholder function that should be replaced with actual fixture preset loading logic.
    """
    return  {
        "time": start_time,
        "fixture": fixture,
        "preset": "flash",
        "parameters": {
            "fade_beats": 1,
            "start_brightness": start_brightness
        },
        "duration": 1,
        "chaser": "ai",
        "chaser_id": "ai_generated_000"
    }


if __name__ == "__main__":

    songs_folder="/home/darkangel/ai-light-show/songs"
    song_name = "born_slippy"
    
    # Create a SongMetadata instance
    song = SongMetadata(song_name, songs_folder=songs_folder, ignore_existing=True)
    print(f"Analyzing: {song_name}")
    
    # Analyze the song
    song = song_analyze(song)
    
    # Save the song metadata
    song.save()