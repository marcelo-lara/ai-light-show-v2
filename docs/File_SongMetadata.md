### Song Metadata

Every song (mp3 file) has a related metadata file in `/songs` with the name `/songs/{fileName}.meta.json`.


#### Top-Level Fields

- **title** (`string`): The title of the track.  
- **genre** (`string`): The genre classification of the track.  
- **duration** (`float`): Duration of the track in seconds.  
- **bpm** (`float`): Beats per minute, indicating tempo.  
- **arrangement** (`object`): Structure of the track divided into sections.
- **key_moments** (`array<object>`): Important timestamped moments in the track.  
- **chords** (`array<object>`): A list of chord entries with timing and harmonic analysis.

##### `arrangement` Object

The `arrangement` property is a list of song sections. Each section includes:

- **`name`**: The section name (e.g., `"Intro"`, `"Chorus"`, `"Instrumental"`).
- **`start`**: Start time of the section in seconds.
- **`end`**: End time of the section in seconds.
- **`prompt`**: (Optional) Description to help LLM to undertand the .

**Example:**
```json
{ "name": "Intro", "start": 1.03, "end": 12.98, "prompt": "" }


Example:
```json
"arrangement": {
  "intro": { "start": 0.0, "duration": 8.0 },
  "verse": { "start": 8.0, "duration": 16.0 }
}
```

##### `key_moments` Object

`key_moments` is a list of significant musical events in the track. Each entry includes:

- **time**: Timestamp (in seconds) when the event occurs.  
- **name**: A short label identifying the moment (e.g., `"Drop"`, `"Bridge"`).  
- **description**: Optional context or notes about what happens musically.  
- **duration**: Length of the event in seconds (typically `0` for instantaneous events).

### Example

```json
{
  "time": 34.21,
  "name": "Drop",
  "description": "Heavy drum starts",
  "duration": 2.55
}
