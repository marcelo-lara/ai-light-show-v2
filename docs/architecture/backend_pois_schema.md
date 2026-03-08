# Backend POIs Schema

`backend/fixtures/pois.json` is the registry of actual POIs (Points of Interest) in the show and their mapping to individual fixtures.

Each entry contains:

- `id`: Unique POI id (e.g. `piano`).
- `name`: Display name.
- `location`: Physical placement `{x, y, z}`.
- `fixtures`: A mapping dictionary of fixture IDs to their target `{pan, tilt}` data.

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
    }
]
```

## POI Management and Lifecycle

1. **PoiDatabase**: The backend uses the `PoiDatabase` class (in `backend/store/pois.py`) to manage the loading, CRUD operations, and on-disk synchronization of `pois.json`.
2. **WebSocket Intents**: The frontend interacts with POIs via explicit real-time intent messages over the WebSocket connection:
   - `poi.create`
   - `poi.update`
   - `poi.delete`
   - `poi.update_fixture_target` (specifies `poi_id`, `fixture_id`, `pan`, and `tilt`)
3. **Frontend Sync**: The frontend `PoiLocationController` enables live adjustments where users can pick a POI, manually adjust slider positions on a moving head, and click "update", immediately publishing the pan/tilt values back using `poi.update_fixture_target`.
4. **Render-time Lookup**: DMX render effects, like `move_to_poi.py`, query the `PoiDatabase` synchronously during playback rendering to instantly find target `pan` and `tilt` values based on a given fixture and requested POI id.
