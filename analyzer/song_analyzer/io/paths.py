"""Path utilities for the analyzer."""

import hashlib
import re
from pathlib import Path


def create_song_slug(filename: str) -> str:
    """Create a stable slug from a song filename."""
    # Remove extension
    name = Path(filename).stem
    # Normalize: lowercase, replace spaces with underscore
    slug = re.sub(r'\s+', '_', name.lower())
    return slug


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def ensure_directory(path: Path):
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)