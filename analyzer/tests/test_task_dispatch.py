from __future__ import annotations

from pathlib import Path

from src.task_queue.dispatch import list_task_types, run_task


def test_task_catalog_includes_init_song() -> None:
    task_types = {item["value"] for item in list_task_types()}
    assert "init-song" in task_types
    assert "find-chord-patterns" in task_types
    assert "find-stem-patterns" in task_types


def test_run_task_init_song_returns_metadata_payload(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()

    result = run_task("init-song", {"song_path": str(song_path), "meta_path": str(tmp_path / "meta")})

    assert result["ok"] is True
    assert result["task_type"] == "init-song"
    assert Path(result["value"]["info_file"]).exists()