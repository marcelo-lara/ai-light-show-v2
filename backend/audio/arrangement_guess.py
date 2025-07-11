from backend.models.song_metadata import SongMetadata, Section

def guess_arrangement_using_drum_patterns(song: SongMetadata) -> SongMetadata:
    """
    Guess the arrangement of the song based on its drum patterns.
    This function will analyze the song's drum patterns to determine sections.
    :param song: SongMetadata object containing the song to analyze.
    :return: Updated SongMetadata object with guessed arrangement.
    """
    return song

def guess_arrangement(song: SongMetadata) -> SongMetadata:
    """
    Guess the arrangement of the song based on its beats and patterns.
    This function will analyze the song's beats and patterns to determine sections.
    :param song: SongMetadata object containing the song to analyze.
    :return: Updated SongMetadata object with guessed arrangement.
    """
    # Placeholder for arrangement guessing logic
    # This could be based on beat patterns, volume changes, etc.
    # For now, we will just create a simple arrangement based on beats
    if not song.beats:
        return song

    # Create a simple arrangement based on beats
    # This is a placeholder logic and should be replaced with actual arrangement logic
    # A song ussually has sections every 16 beats (4 bars at 4/4 time)
    section_length = 16
    arrangement  = list()
    for i in range(0, len(song.beats), section_length):
        section_beats = song.beats[i:i + section_length]
        if section_beats:
            section_start = section_beats[0]['time']
            section_end = section_beats[-1]['time']
            section_volume = sum(beat['volume'] for beat in section_beats) / len(section_beats)
           
            # Create a new section with the calculated properties
            section = Section(
                f"Section {len(arrangement) + 1}", 
                section_start, 
                section_end, 
                f"{section_length} beats | volume: {section_volume}"
            )
            arrangement.append(section)

    song.arrangement = arrangement            
    return song

if __name__ == "__main__":
    
    # Example usage
    song = SongMetadata('Despina Vandi - Geia')
    song = guess_arrangement(song)
    print(song.arrangement)  # Should print the guessed arrangement sections