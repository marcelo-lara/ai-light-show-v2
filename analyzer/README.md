# Analyzer

This module analyzes songs for beats, stems, and audio features using Essentia.

TODO: implement a unified "info.json" manager, so every analysis step could add their artifacts.

## Running

**Always run inside Docker.**

### Start the Analyzer Container
```bash
docker compose up analyzer --build
```

### Interactive Mode
```bash
docker compose exec analyzer python analyze_song.py
```
Follow the menu prompts to select songs and analyses.

### CLI Mode
Run specific analyses non-interactively:
```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --essentia-analysis --beat-finder
```

#### CLI Options
- `--song <filename>`: Song file name in `/app/songs` (recommended to pass explicitly)
- `--split-stems`: Run Demucs stem separation
- `--beat-finder`: Run librosa beat and downbeat detection
- `--essentia-analysis`: Run Essentia analysis (key, BPM, beats, rhythm descriptors, onsets, beat loudness)

### Outputs
- **Beats**: `/app/meta/<song>/beats.json` (beat/downbeat times)
- **Stems**: `/app/meta/<song>/stems/` (separated audio files)
- **Essentia**: `/app/meta/<song>/essentia/<artifact>.json` (features) and `<artifact>.svg` (plots) for mix and stems
- **Metadata**: `/app/meta/<song>/info.json` updated with artifact paths

## Testing

Use the real analyzer flow to verify Essentia analysis:
```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --essentia-analysis
```

Then confirm artifacts exist in `/app/meta/Armin - Revolution/essentia/` (e.g., `rhythm.json`, `loudness_envelope.json`, etc.).