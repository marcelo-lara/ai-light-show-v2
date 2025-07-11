# 📄 `fixtures.json` – Lighting Fixture Definitions

This file contains definitions for all DMX lighting fixtures used in the system. Each fixture entry includes its DMX channel mapping, supported effects, presets, and rendering metadata.

---

## 📁 Structure

```json
[
  { ... },  // Fixture 1
  { ... },  // Fixture 2
  ...
]
```

Each object represents a **fixture**.

---

## 🔧 Fixture Object

| Field            | Type     | Description                                                                                 |
| ---------------- | -------- | ------------------------------------------------------------------------------------------- |
| `id`             | `string` | Unique internal ID for the fixture (e.g., `"parcan_l"`, `"head_el150"`).                    |
| `name`           | `string` | Human-readable name for display purposes.                                                   |
| `type`           | `string` | Fixture category: `"rgb"` or `"moving_head"`.                                               |
| `channels`       | `object` | Mapping of logical names (e.g., `"red"`, `"pan_msb"`) to 1-based DMX channel numbers.       |
| `current_values` | `object` | DMX values for all channels at a given moment (used for state tracking).                    |
| `presets`        | `array`  | Named presets (e.g., positions or colors) defined by a `name` and `values` object.          |
| `effects`        | `array`  | List of supported effects such as `"strobe"`, `"flash"`, `"fade"`, `"seek"`, etc.           |
| `arm`            | `object` | Defines the channels and values required to "arm" or enable the fixture (e.g., `"dim": 255`). |
| `meta`           | `object` | Metadata used for rendering and interpretation (see below).                                 |

---

## `meta` Field

Contains fixture specific definitions used to "paint" (transform effects or cues in the DmxCanvas object)

### `channel_types`

```json
"channel_types": {
  "red": "color",
  "pan": "position_16bit",
  "shutter": "strobe",
  ...
}
```

Describes how each channel behaves. Common types:

* `"color"` – used for RGB or color wheels.
* `"position_16bit"` – used for pan/tilt with MSB + LSB.
* `"dimmer"` – continuous brightness.
* `"strobe"` – for flashing or pulsing.
* `"wheel"` – for gobos or color wheels with discrete values.

---

### `value_mappings`

```json
"value_mappings": {
  "color": {
    "0": "White",
    "25": "Orange",
    ...
  },
  "gobo": {
    "50": "BigOval",
    ...
  }
}
```

Maps discrete DMX values to human-readable names (used for UI or logic reasoning with wheels).

---

### `position_constraints` 


```json
"position_constraints": {
  "pan": { "min": 0, "max": 65535 },
  "tilt": { "min": 70, "max": 3363 }
}
```

Defines the physical movement limits of a moving head fixture. These are used to:

* Clamp pan/tilt positions to usable zones.
* Normalize movement paths across multiple fixtures.

---

## ✅ Example: Moving Head

```json
{
  "id": "head_el150",
  "type": "moving_head",
  "channels": {
    "pan_msb": 1,
    "pan_lsb": 2,
    "tilt_msb": 3,
    "tilt_lsb": 4,
    "color": 8,
    "gobo": 9
  },
  "presets": [
    {
      "name": "Piano",
      "values": {
        "pan": 120,
        "pan_fine": 35,
        "tilt": 20,
        "tilt_fine": 11
      }
    }
  ],
  "effects": ["full", "flash", "seek"],
  "arm": { "shutter": 255 },
  "meta": {
    "channel_types": {
      "pan": "position_16bit",
      "tilt": "position_16bit",
      "color": "wheel",
      "gobo": "wheel"
    },
    "value_mappings": {
      "color": { "0": "White", "25": "Orange", "175": "Red" },
      "gobo": { "0": "Open", "25": "Tunnel" }
    },
    "position_constraints": {
      "pan": { "min": 0, "max": 65535 },
      "tilt": { "min": 70, "max": 3363 }
    }
  }
}
```
