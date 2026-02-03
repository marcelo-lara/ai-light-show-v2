import os
from spleeter.separator import Separator

def split_stems(input_file, stems_folder, stems=['vocals', 'drums', 'bass', 'other']):
    '''
    Receives an audio file and splits it into stems using a pre-trained model.
    
    :param input_file: source audio file
    :param stems_folder: folder to save the stems
    :param stems: list of stems to extract
    '''
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    if not os.path.exists(stems_folder):
        os.makedirs(stems_folder, exist_ok=True)

    # Determine configuration based on number of request stems or force 4stems default
    # Spleeter commonly supports 2, 4, or 5 stems.
    if len(stems) == 2:
        configuration = 'spleeter:2stems'
    elif len(stems) == 5:
        configuration = 'spleeter:5stems'
    else:
        # Default to 4 stems (vocals, drums, bass, other)
        configuration = 'spleeter:4stems'

    # Check for empty model directory which causes spleeter to fail silently
    model_name = configuration.split(':')[1]
    model_path = os.path.join("pretrained_models", model_name)
    if os.path.exists(model_path) and not os.listdir(model_path):
        print(f"Found empty model directory at {model_path}. Removing it to force re-download.")
        os.rmdir(model_path)

    print(f"Initializing separator with {configuration}...")
    separator = Separator(configuration)

    print(f"Splitting {input_file}...")
    # This will create a subfolder in stems_folder named after the input file
    separator.separate_to_file(input_file, stems_folder)
    
    print("Stem splitting complete.")
    return stems_folder

if __name__ == "__main__":
    song_path = os.path.join(SONGS_FOLDER, SAMPLE_SONG)
    if os.path.exists(song_path):
        split_stems(song_path, TEMP_FOLDER)
    else:
        print(f"Sample song not found at {song_path}")