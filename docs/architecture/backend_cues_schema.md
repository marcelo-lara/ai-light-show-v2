# Backend Cues Schema

`backend/cues/{song_name}.json` stores a JSON array of cue entries for a song.

## Top-level shape

The file content is an array.

```json
[
  {
    "time": 1.0,
    "fixture_id": "parcan_l",
    "effect": "flash",
    "duration": 0.5,
    "data": {},
    "name": null,
    "created_by": "user"
  }
]
```

## Cue entry shape

Each array item is an object with these fields:

- `time`: number. Cue start time in seconds.
- `fixture_id`: string. Fixture identifier.
- `effect`: string. Effect name for the target fixture.
- `duration`: number. Effect duration in seconds.
- `data`: object. Effect-specific parameter payload.
- `name`: string or `null`. Display label for the cue.
- `created_by`: string. Origin of the cue entry.

## Example

```json
[
  {
    "time": 1.0,
    "fixture_id": "parcan_l",
    "effect": "flash",
    "duration": 0.5,
    "data": {},
    "name": null,
    "created_by": "user"
  },
  {
    "time": 3.0,
    "fixture_id": "parcan_l",
    "effect": "strobe",
    "duration": 1.0,
    "data": {
      "rate": 10
    },
    "name": null,
    "created_by": "user"
  }
]
```
