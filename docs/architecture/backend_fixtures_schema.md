# Backend Fixture Schema

Fixture data is split into two JSON document types under `backend/fixtures/`.

## 1. Fixture instances

`backend/fixtures/fixtures.json` is the registry of actual fixtures in the show.

Each entry contains only instance-specific data:

- `id`: Unique runtime fixture id.
- `name`: Display name.
- `fixture`: Template reference key (e.g., `mini_beam_prism`).
- `base_channel`: First DMX channel used by the fixture instance (1-based internally, offset 0 in templates).
- `location`: Physical placement `{x, y, z}`.

Example:

```json
{
	"id": "mini_beam_prism_l",
	"name": "Mini Beam Prism (L)",
	"fixture": "mini_beam_prism",
	"base_channel": 42,
	"location": {
		"x": 0.15,
		"y": 0.2,
		"z": 0.0
	}
}
```

## 2. Fixture templates

Each reusable fixture model lives in its own file named `backend/fixtures/fixture.<type>.<model>.json`.

Template files define:

- `id`: Internal model identifier.
- `type`: Category (e.g., `moving_head`, `parcan`).
- `channels`: Map of logical channel names to 0-based offsets.
- `effects`: List of supported effect keys.
- `meta_channels`: Dictionary of high-level controls mapping directly to DMX logic.
  - `label`: UI display label.
  - `kind`: Data type (`u8`, `u16`, `rgb`, `enum`).
  - `channel`: Single 0-based offset name from `channels`.
  - `channels`: Array of 0-based offset names for multi-channel types (e.g., `u16` MSB/LSB, `rgb`).
  - `mapping`: (Optional) Key in `mappings` for labeled or discrete values (e.g., `Gobo Wheel`).
  - `step`: (Optional) Boolean. If `true` for `kind: "enum"`, indicates the values represent discrete physical steps/indices (like a Color Wheel) rather than just functional labels (like Reset).
  - `arm`: (Optional) Default DMX value (0-255).
  - `hidden`: (Optional) Boolean to hide from UI.
- `mappings`: Dictionary for `enum` or labeled `u8` values.

### Example Template Excerpt (Flattened Schema)

```json
"meta_channels": {
    "pan": {
        "label": "Pan",
        "kind": "u16",
        "channels": ["pan_msb", "pan_lsb"]
    },
    "strobe": {
        "label": "Strobe",
        "kind": "u8",
        "mapping": "strobe",
        "channel": "strobe"
    }
}
```

## Channel addressing rule

Template channel numbers are offsets relative to an instance's `base_channel`.

```text
real_dmx_channel = base_channel + template_channel_offset
```

## Follow-up implementation

The backend loader must resolve the `fixture` reference, load the template, and materialize absolute runtime channels from `base_channel + offset` before instantiating runtime fixture models.
