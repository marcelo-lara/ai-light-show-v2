# %% [markdown]
# This module generates song metadata to be used by LLM for analysis and visualization.

# %% [code]
# Constants for sample song paths
SONGS_FOLDER = "songs/"
TEMP_FOLDER = "temp_files/"
SAMPLE_SONG = "sono - keep control.mp3"

# %% [code]
# Split stems from the song
import os
from split_stems import split_stems

song_path = os.path.join(SONGS_FOLDER, SAMPLE_SONG)
if os.path.exists(song_path):
    split_stems(song_path, TEMP_FOLDER)

# %% [code]
# Extract drums time data

