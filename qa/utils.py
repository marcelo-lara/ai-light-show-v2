import os
import shutil
from pathlib import Path

def safe_name(test_name: str) -> str:
    """Sanitize test name for filename use."""
    return test_name.replace(" ", "_").replace("/", "_").lower()

def ensure_dir(path: str):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)

def copy_overwrite(src: str, dst: str):
    """Copy a file, overwriting destination if it exists."""
    if os.path.exists(src):
        shutil.copy2(src, dst)
