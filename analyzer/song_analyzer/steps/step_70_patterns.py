import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import json
import numpy as np

from ..io.json_write import stable_write_json
from ..models.failures import FailureRecord


@dataclass
class StepResult:
    name: str
    status: str
    artifacts: list
    seconds: float = 0.0
    failure: Optional[FailureRecord] = None


def run(song_path: Path, out_dir: Path, temp_dir: Path, cfg):
    start = time.time()
    beats_path = out_dir / "analysis" / "beats.json"
    onsets_path = out_dir / "analysis" / "onsets.json"
    try:
        with open(beats_path, 'r', encoding='utf-8') as fh:
            beats = json.load(fh).get('beats', [])
        with open(onsets_path, 'r', encoding='utf-8') as fh:
            events = json.load(fh).get('events', [])
        if not beats or not events:
            raise ValueError("beats or events missing")
        # Quantize onto 16th grid per bar assuming 4/4 and tempo from beat spacing
        # Simple approach: compute beats per bar and make per-bar binary vector
        grid = []
        # Map events to nearest beat time modulo 1 bar
        bpms = 60.0 / np.diff(beats).mean()
        # Assume 4 beats per bar
        subdivision = 16
        patterns = {}
        occurrences = []
        # naive windowing: for each bar starting at beats[0] step 4 beats
        samples = []
        for i in range(0, len(beats), 4):
            bar_start = beats[i]
            bar_end = beats[i+4] if i+4 < len(beats) else beats[-1]
            dt = (bar_end - bar_start) / subdivision if (bar_end - bar_start) > 0 else 0.5
            vec = [0]*subdivision
            for e in events:
                t = e['time_s'] if 'time_s' in e else e.get('time', None)
                if t is None:
                    continue
                if bar_start <= t < bar_end:
                    idx = int((t - bar_start) / dt)
                    if 0 <= idx < subdivision:
                        vec[idx] = 1
            key = tuple(vec)
            patterns.setdefault(key, {'count':0, 'occurrences':[]})
            patterns[key]['count'] += 1
            patterns[key]['occurrences'].append(bar_start)
        canonical = []
        occs = []
        pid = 1
        for k,v in patterns.items():
            if v['count'] > 1:
                pid_str = f"p{pid:03d}"
                canonical.append({"pattern_id": pid_str, "type": "drums", "length_bars": 1, "tracks": {"kick": list(k)}, "confidence": 0.5})
                for s in v['occurrences']:
                    occs.append({"pattern_id": pid_str, "start_s": s, "bars":1, "confidence":0.5})
                pid += 1
        out = {"schema_version":"1.0", "grid": {"subdivision": "1/16", "reference": "analysis/beats.json"}, "patterns": canonical, "occurrences": occs}
        path = out_dir / "show_plan" / "patterns.json"
        stable_write_json(path, out)
        seconds = time.time() - start
        return StepResult(name="patterns", status="ok", artifacts=[str(path)], seconds=seconds)
    except Exception as exc:
        seconds = time.time() - start
        failure = FailureRecord(code="MODEL_ERROR", message=str(exc), detail=repr(exc), exception_type=type(exc).__name__, retryable=False)
        return StepResult(name="patterns", status="failed", artifacts=[], seconds=seconds, failure=failure)
