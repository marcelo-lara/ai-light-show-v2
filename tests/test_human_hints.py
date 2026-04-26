from pathlib import Path

from models.song.human_hints import HumanHints


def test_human_hints_load_existing_contract() -> None:
    meta_root = Path(__file__).resolve().parents[1] / "data" / "output"

    hints = HumanHints(meta_root, "Cinderella - Ella Lee")

    assert hints.file_exists is True
    assert hints.song_name == "Cinderella - Ella Lee"
    assert len(hints.list()) >= 2
    assert hints.list()[0]["id"] == "ui_001"


def test_human_hints_create_save_update_delete(tmp_path: Path) -> None:
    meta_root = tmp_path / "output"
    meta_root.mkdir()

    hints = HumanHints(meta_root, "demo song")

    assert hints.file_exists is False
    assert hints.status() == {"dirty": False, "saved": True, "file_exists": False}

    created = hints.create({
        "start_time": 1.25,
        "end_time": 2.5,
        "title": "Accent",
        "summary": "Builds pressure.",
        "lighting_hint": "Hold a narrow look.",
    })
    assert created["id"] == "ui_001"
    assert hints.status()["dirty"] is True

    hints.save()
    assert hints.path.exists() is True
    assert hints.status() == {"dirty": False, "saved": True, "file_exists": True}

    updated = hints.update(created["id"], {"end_time": 3.0, "title": "Accent A"})
    assert updated is not None
    assert updated["title"] == "Accent A"
    hints.save()

    reloaded = HumanHints(meta_root, "demo song")
    assert reloaded.list()[0]["end_time"] == 3.0
    assert reloaded.delete(created["id"]) is True
    reloaded.save()
    assert reloaded.list() == []