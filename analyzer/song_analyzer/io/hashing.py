"""Hashing utilities."""

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    hash_obj = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()