from pathlib import Path
import re


def make_slug(filename: str) -> str:
    name = Path(filename).stem
    name = name.lower().strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_\-]", "", name)
    return name


def ensure_dirs(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    return path
