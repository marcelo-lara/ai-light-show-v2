"""JSON writing utilities with consistent formatting."""

import json
from pathlib import Path
from typing import Any


def write_json(data: Any, path: Path, precision: int = 6):
    """Write data to JSON file with consistent formatting."""

    def round_floats(obj):
        """Recursively round floats to specified precision."""
        if isinstance(obj, float):
            return round(obj, precision)
        elif isinstance(obj, dict):
            return {k: round_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [round_floats(item) for item in obj]
        else:
            return obj

    # Round floats and sort keys
    processed_data = round_floats(data)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=2, sort_keys=True, ensure_ascii=False)