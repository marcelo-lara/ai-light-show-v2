from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .models import ChaserDefinition


def load_chasers(chasers_dir: Path) -> List[ChaserDefinition]:
    if not chasers_dir.exists() or not chasers_dir.is_dir():
        return []

    chasers: List[ChaserDefinition] = []
    for chaser_file in sorted(chasers_dir.glob("*.json")):
        with open(chaser_file, "r", encoding="utf-8") as handle:
            raw = json.load(handle)

        if not isinstance(raw, dict):
            raise ValueError(f"chasers_schema_invalid:{chaser_file.name}")
        chasers.append(ChaserDefinition(**raw))

    return chasers


def upsert_global_chaser(chasers_dir: Path, definition: ChaserDefinition) -> None:
    chasers_dir.mkdir(parents=True, exist_ok=True)
    target = chasers_dir / f"{definition.id}.json"
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(definition.model_dump(), handle, indent=2)
        handle.write("\n")


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
