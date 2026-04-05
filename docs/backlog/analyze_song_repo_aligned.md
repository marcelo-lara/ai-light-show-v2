# 🎧 Analyze Song Service — Repo-Aligned Implementation (ai-light-show-v2)

> This version is **aligned to your current repository structure** so VSCode Copilot can edit in-place.

---

# 🎯 Goal

Implement:

- Layer A — Harmonic summary  
- Layer B — Symbolic summary  
- Layer C — Energy summary  

Expose:

`POST /analyzer/analyze-song`

Artifacts:

analyzer/output/{song_id}/
  ├── layer_a_harmonic.json
  ├── layer_b_symbolic.json
  ├── layer_c_energy.json
  └── music_feature_layers.json

---

# 🧱 Integration with Current Repo

Extend:

analyzer/
  api/
  features/
  core/
  output/

Add:

analyzer/
  api/analyze_song.py
  features/harmonic/
  features/symbolic/
  features/energy/
  core/timeline.py
  merge.py

---

# 🚀 1. API Endpoint (Analyzer)

```python
from fastapi import APIRouter
from pathlib import Path
import json

from analyzer.core.timeline import build_timeline
from analyzer.features.energy.pipeline import compute_energy_layer
from analyzer.features.symbolic.pipeline import compute_symbolic_layer
from analyzer.features.harmonic.pipeline import compute_harmonic_layer
from analyzer.merge import merge_layers

router = APIRouter()

@router.post("/analyze-song")
def analyze_song(payload: dict):

    song_id = payload["song_id"]
    audio_path = Path(payload["audio_path"])
    stems_path = payload.get("stems_path")

    output_dir = Path("analyzer/output") / song_id
    output_dir.mkdir(parents=True, exist_ok=True)

    timeline = build_timeline(audio_path)

    layer_c = compute_energy_layer(audio_path, timeline)
    layer_b = compute_symbolic_layer(audio_path, timeline, stems_path)
    layer_a = compute_harmonic_layer(audio_path, timeline)

    merged = merge_layers(layer_a, layer_b, layer_c, timeline)

    _write(output_dir / "layer_a_harmonic.json", layer_a)
    _write(output_dir / "layer_b_symbolic.json", layer_b)
    _write(output_dir / "layer_c_energy.json", layer_c)
    _write(output_dir / "music_feature_layers.json", merged)

    return {
        "ok": True,
        "song_id": song_id,
        "output_dir": str(output_dir)
    }

def _write(path: Path, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
```

---

# 🧠 2. Timeline

```python
def build_timeline(audio_path):
    return {
        "tempo": 120,
        "beats": [],
        "bars": [],
        "sections": []
    }
```

---

# 🔊 3. Layer C — Energy

```python
def compute_energy_layer(audio_path, timeline):
    return {
        "loudness": {"mean": 0.0, "peak": 0.0},
        "onset_strength": [],
        "spectral_centroid": [],
        "spectral_flux": [],
        "stem_energy_distribution": [],
        "sections": timeline["sections"],
        "summary": {"energy_trend": "unknown"}
    }
```

---

# 🎹 4. Layer B — Symbolic

```python
def compute_symbolic_layer(audio_path, timeline, stems_path=None):
    return {
        "notes": [],
        "density_per_bar": [],
        "melodic_contour": [],
        "bass_movement": [],
        "summary": {"texture": "unknown"}
    }
```

---

# 🎼 5. Layer A — Harmonic

```python
def compute_harmonic_layer(audio_path, timeline):
    return {
        "chords": [],
        "key": None,
        "summary": {"progression": []}
    }
```

---

# 🔗 6. Merge

```python
def merge_layers(layer_a, layer_b, layer_c, timeline):
    return {
        "timeline": timeline,
        "layers": {
            "harmonic": layer_a,
            "symbolic": layer_b,
            "energy": layer_c
        }
    }
```

---

# 🧪 Test

```bash
curl -X POST http://localhost:8000/analyze-song \
  -H "Content-Type: application/json" \
  -d '{"song_id":"Yonaka - Seize the Power","audio_path":"./songs/Yonaka - Seize the Power.mp3"}'
```

---

# 🚀 Implementation Order

1. Timeline  
2. Energy  
3. Merge  
4. Endpoint  
5. Symbolic  
6. Harmonic  

---

# 💡 Rule

Keep contracts stable.  
Do not optimize early.  
