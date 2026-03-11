# Backend POIs Schema

`backend/fixtures/pois.json` stores points of interest (POIs) and optional per-fixture pan/tilt targets.

## POI record shape

Each POI contains:
- `id`: unique POI id.
- `name`: display name.
- `location`: `{x, y, z}`.
- `fixtures` (optional): fixture-id map to `{pan, tilt}` values.

Example:

```json
[
  {
    "id": "piano",
    "name": "Piano",
    "location": {"x": 0.5, "y": 0.5, "z": 0},
    "fixtures": {
      "mini_beam_prism_l": {"pan": 123, "tilt": 456},
      "mini_beam_prism_r": {"pan": 789, "tilt": 1011}
    }
  },
  {
    "id": "reference_only",
    "name": "Reference Point",
    "location": {"x": 0.0, "y": 0.0, "z": 1.0}
  }
]
```

## POI management

Backend class: `backend/store/pois.py::PoiDatabase`.

Supported operations:
- `create(poi_data)`
- `update(poi_id, poi_data)`
- `delete(poi_id)`
- `get_all()`, `get(poi_id)`
- `reload()`, `save()`

Storage behavior:
- CRUD writes back to `pois.json` after in-memory mutation.
- Data is stored as a list of dictionaries.

## WebSocket intents

POI intents handled by backend:
- `poi.create`
- `poi.update`
- `poi.delete`
- `poi.update_fixture_target`

`poi.update_fixture_target` payload:
- `poi_id`
- `fixture_id`
- `pan`
- `tilt`

Backend behavior for `poi.update_fixture_target`:
- Validates `poi_id` and `fixture_id` presence.
- Clamps pan/tilt to `0..65535`.
- Ensures POI has a `fixtures` object, then writes target values.
- Marks canvas dirty.

## Runtime lookup during render

Moving-head POI effects resolve targets through `PoiDatabase.get_fixture_target_sync`.

Lookup behavior is case-insensitive for:
- `poi_id`
- `fixture_id`

If POI or fixture target is missing, POI-dependent effects no-op for that frame.
