from __future__ import annotations

from pathlib import Path

import pytest

from src.task_queue.dispatch import list_task_types, run_task
from src.tasks.catalog import run_registered_task


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


def test_run_registered_task_releases_model_memory_on_failure(monkeypatch, tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    cleanup_calls: list[str] = []

    def failing_runner(params, progress_callback=None):
        del params, progress_callback
        raise RuntimeError("boom")

    monkeypatch.setitem(
        run_registered_task.__globals__["TASKS_BY_TYPE"],
        "failing-task",
        {"value": "failing-task", "runner": failing_runner},
    )
    monkeypatch.setitem(run_registered_task.__globals__, "release_model_memory", lambda: cleanup_calls.append("cleanup"))

    with pytest.raises(RuntimeError, match="boom"):
        run_registered_task("failing-task", {"song_path": str(song_path)})

    assert cleanup_calls == ["cleanup"]
    run_registered_task.__globals__["TASKS_BY_TYPE"].pop("failing-task", None)