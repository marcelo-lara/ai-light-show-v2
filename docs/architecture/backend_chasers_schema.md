# Backend Chasers Schema

`backend/chasers/*.json` stores reusable chaser definitions (one definition per file).

## Top-level shape

Each file under `backend/chasers` stores a single chaser definition object.
The filename should match the definition id (`{id}.json`).

```json
{
  "id": "downbeats_and_beats",
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
```

## Chaser definition shape

Each file object includes these fields:

- `id`: string. Stable chaser identifier used by `chaser.*` intents and cue-sheet `chaser_id` entries.
- `name`: string. Human-readable label shown in the UI.
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

The backend persists chaser cue rows with `chaser_id` in the cue sheet.
Runtime expansion to effect entries in seconds happens only during DMX canvas rendering and chaser preview.
