import json
from decimal import Decimal
from pathlib import Path
from typing import Any


class _FloatRounder(json.JSONEncoder):
    def default(self, o: Any):
        if isinstance(o, float):
            return float(Decimal(o).quantize(Decimal('0.000001')))
        return super().default(o)


def stable_write_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True, cls=_FloatRounder)
    return path
