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

def rotate_artifacts(artifacts_dir: str, pattern: str, max_count: int = 5):
    """
    Keep only the most recent N files matching the pattern in artifacts_dir.
    Files are assumed to have a timestamp-sortable prefix.
    """
    path = Path(artifacts_dir)
    files = sorted(list(path.glob(pattern)), key=lambda x: x.name, reverse=True)
    
    if len(files) > max_count:
        for f in files[max_count:]:
            try:
                f.unlink()
            except Exception as e:
                print(f"Failed to delete old artifact {f}: {e}")
