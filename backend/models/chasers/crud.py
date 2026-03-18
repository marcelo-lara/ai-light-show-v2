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


def get_chaser_by_id(chasers: List[ChaserDefinition], chaser_id: str) -> Optional[ChaserDefinition]:
    lookup = str(chaser_id or "").strip().lower()
    if not lookup:
        return None
    for chaser in chasers:
        if chaser.id.strip().lower() == lookup:
            return chaser
    return None


def get_chaser_by_name(chasers: List[ChaserDefinition], name: str) -> Optional[ChaserDefinition]:
    lookup = str(name or "").strip().lower()
    if not lookup:
        return None
    for chaser in chasers:
        if chaser.name.strip().lower() == lookup:
            return chaser
    return None


def get_chaser_cycle_beats(chaser: ChaserDefinition) -> float:
    return max((float(effect.beat) + float(effect.duration) for effect in chaser.effects), default=0.0)
