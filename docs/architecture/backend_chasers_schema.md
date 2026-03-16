# Backend Chasers Schema

`backend/fixtures/chasers.json` stores reusable chaser definitions.

## Top-level shape

The file content is an array.

```json
[
  {
    "name": "Downbeat plus two beats",
    "description": "A simple chaser pattern",
    "effects": [
      {
        "beat": 0.0,
        "fixture_id": "parcan_pl",
        "effect": "flash",
        "duration": 1.5,
        "data": {}
      }
    ]
  }
]
```

## Chaser definition shape

Each array item is an object with these fields:

- `name`: string. Unique chaser name used by `chaser.*` intents.
- `description`: string. Human-readable summary.
- `effects`: array of effect rows.

## Chaser effect row shape

Each `effects` item contains:

- `beat`: number. Effect start offset in beats from the chaser start.
- `fixture_id`: string. Target fixture identifier.
- `effect`: string. Effect name for the target fixture.
- `duration`: number. Effect duration in beats.
- `data`: object. Effect-specific parameters.

## Beat timing semantics

`beat` and `duration` are measured in beats. Runtime conversion uses `beatToTimeMs(beat_count, bpm)`.

Examples at `bpm = 120`:

- `beatToTimeMs(1.0, 120) = 500`
- `beatToTimeMs(1.5, 120) = 750`

The backend converts chaser rows to cue entries in seconds for cue-sheet persistence and DMX canvas rendering.
