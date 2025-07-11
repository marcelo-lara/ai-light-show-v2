from pathlib import Path

def extract_stems(input_file: str, songs_temp_folder: str = '', song_prefix: str = '', stems: str = 'all', model: str = ''):
    """
    Extract stems from an audio file using Demucs.
    :param input_file: Path to the input audio file.
    :param songs_temp_folder: Folder to store temporary output files.
    :param song_prefix: Prefix for the output files.
    :param stems: Type of stems to extract ('vocals', 'drums', 'bass', 'other', or 'all').
    :param model: Model to use for separation (optional: 'htdemucs_ft', 'mdx_extra') [https://github.com/facebookresearch/demucs?tab=readme-ov-file#separating-tracks].
    :return: Dictionary with output paths.
    :raises RuntimeError: If Demucs fails to run.
    """
    # set default values if not provided
    if song_prefix == '':
        song_prefix = input_file.split("/")[-1].split(".")[0]
    if songs_temp_folder == '':
        songs_temp_folder = str(Path(input_file).parent) + '/temp'

    # prepare command
    import subprocess
    command = [
        "python", "-m", "demucs.separate", 
        "-o", songs_temp_folder,
        *(["--two-stems=" + stems] if stems != 'all' else []),
        *(["-n=" + model] if model else []),
        input_file        
    ]
    
    # execute command
    print("🎵 Extracting stems from the song...")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.returncode != 0:
            print(f"Error running Demucs: {result.stderr}")
            raise RuntimeError(f"Demucs failed with error: {result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"Command: {' '.join(command)}")
        print(f"Error running Demucs: {e.stderr}")
        raise RuntimeError(f"Demucs failed with error: {e.stderr}")

    # return output paths
    output_folder = f"{songs_temp_folder}/htdemucs/{song_prefix}"
    return {
        "output_folder": output_folder
    }

## Example usage:
if __name__ == "__main__":
    song_file = "/home/darkangel/ai-light-show/songs/born_slippy.mp3"

    print(f"Extracting drums from {song_file}...")
    results = extract_stems(song_file, stems='drums')
    print("-----------")
