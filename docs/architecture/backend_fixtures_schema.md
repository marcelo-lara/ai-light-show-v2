# Backend Fixture Schema

Fixture data is split across instance records and template records under `backend/fixtures/`.

## 1. Fixture instances

`backend/fixtures/fixtures.json` stores real fixtures in the show.

Each instance row contains:
- `id`: runtime fixture id.
- `name`: display name.
- `fixture`: template key (current data uses keys like `fixture.moving_head.mini_beam_prism`).
- `base_channel`: 1-based starting channel.
- `location`: physical coordinates `{x, y, z}`.

Example:

```json
{
  "id": "mini_beam_prism_l",
  "name": "Mini Beam Prism (L)",
  "fixture": "fixture.moving_head.mini_beam_prism",
  "base_channel": 42,
  "location": {"x": 0.15, "y": 0.2, "z": 0.0}
}
```

## 2. Fixture templates

Each reusable fixture model is a file named `backend/fixtures/fixture.<type>.<model>.json`.

Template fields:
- `id`: model id (for example `mini_beam_prism`).
- `type`: fixture category (for example `moving_head`, `parcan`).
- `channels`: channel-name to zero-based offset mapping.
- `effects`: effect ids that this model declares.
- `meta_channels`: high-level controls used by frontend/API.
- `mappings`: enum/label mappings.

`meta_channels` fields:
- `label`
- `kind`: `u8` | `u16` | `rgb` | `enum`
- `channel` (single channel name)
- `channels` (multi-channel names, e.g. pan/tilt MSB/LSB)
- `mapping` (mapping key in `mappings`)
- `step` (optional enum step semantics)
- `arm` (optional startup/default value)
- `hidden` (optional UI hint)

## Loader behavior

`StateManager.load_fixtures` loads templates and registers each template under:
- `template.id`
- template filename stem (`fixture.<type>.<model>`)

Instance `fixture` keys are matched against this template map.

## Channel addressing rule

Template channel numbers are offsets from instance `base_channel`:

```text
absolute_channel = base_channel + offset
```

Example:
- `base_channel = 42`
- template offset for `dim` = `5`
- absolute DMX channel = `47`

## Runtime materialization

At load time, backend instantiates concrete fixture classes (`MovingHead` or `Parcan`) and computes:
- `channels` (relative offsets)
- `absolute_channels` (resolved 1-based addresses)
- `meta_channels` and `mappings` from template
