# Backend Cues Schema

`backend/cues/{song_name}.json` stores a JSON array of cue entries for a song.
The cue sheet uses a mixed schema: each entry is either an effect cue or a chaser cue.

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
  },
  {
    "time": 1.36,
    "chaser_id": "blue_parcan_chase",
    "data": {
      "repetitions": 1
    },
    "name": null,
    "created_by": "user"
  }
]
```

## Cue entry shape

Each array item is one of these shapes.

### Effect cue

- `time`: number. Cue start time in seconds.
- `fixture_id`: string. Fixture identifier.
- `effect`: string. Effect name for the target fixture.
- `duration`: number. Effect duration in seconds.
- `data`: object. Effect-specific parameter payload.
- `name`: string or `null`. Display label for the cue.
- `created_by`: string. Origin of the cue entry.

### Chaser cue

- `time`: number. Cue start time in seconds.
- `chaser_id`: string. Stable chaser identifier from `backend/fixtures/chasers.json`.
- `data`: object. Chaser cue parameter payload.
- `data.repetitions`: integer. Number of chaser cycles to render; defaults to `1`.
- `name`: string or `null`. Display label for the cue.
- `created_by`: string. Origin of the cue entry.

## Validation rules

- A cue entry must store exactly one mode:
  - effect cue with `fixture_id` + `effect`
  - chaser cue with `chaser_id`
- Effect cues must reference a real fixture and a supported effect for that fixture.
- Chaser cues must reference a valid `chaser_id` from `backend/fixtures/chasers.json`.
- Chaser cue rows are persisted as chaser rows and are expanded into effect renders only at DMX canvas and preview time.

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
  },
  {
    "time": 4.04,
    "chaser_id": "downbeats_and_beats",
    "data": {
      "repetitions": 2
    },
    "name": null,
    "created_by": "user"
  }
]
```
