from pathlib import Path


DOCKER_META_ROOT = Path("/app/meta")
DOCKER_SONGS_ROOT = Path("/app/songs")


def resolve_songs_root(backend_path: Path) -> Path:
    if DOCKER_SONGS_ROOT.exists():
        return DOCKER_SONGS_ROOT
    return backend_path.parent / "analyzer" / "songs"


def resolve_meta_root(backend_path: Path) -> Path:
    if DOCKER_META_ROOT.exists():
        return DOCKER_META_ROOT
    analyzer_meta = backend_path.parent / "analyzer" / "meta"
    if analyzer_meta.exists():
        return analyzer_meta
    return backend_path / "meta"