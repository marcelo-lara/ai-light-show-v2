from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .models import ChaserDefinition


def load_chasers(chasers_file: Path) -> List[ChaserDefinition]:
    if not chasers_file.exists():
        return []

    with open(chasers_file, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, list):
        raise ValueError("chasers_schema_invalid")

    return [ChaserDefinition(**item) for item in raw]


def get_chaser_by_name(chasers: List[ChaserDefinition], name: str) -> Optional[ChaserDefinition]:
    lookup = str(name or "").strip().lower()
    if not lookup:
        return None
    for chaser in chasers:
        if chaser.name.strip().lower() == lookup:
            return chaser
    return None
