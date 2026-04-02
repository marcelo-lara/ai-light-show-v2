import pytest

from backend.api.intents.analyzer.actions.enqueue import enqueue_analyzer_item
from backend.api.intents.analyzer.actions.enqueue_full_artifact import enqueue_full_artifact_playlist
from backend.api.intents.analyzer.actions.execute import execute_analyzer_item
from backend.api.intents.analyzer.actions.execute_all import execute_all_analyzer_items
from backend.api.intents.analyzer.actions.remove import remove_analyzer_item
from backend.api.intents.analyzer.actions.remove_all import remove_all_analyzer_items
from backend.api.intents.analyzer.handlers import ANALYZER_HANDLERS


class _AnalyzerService:
    def __init__(self):
        self.enqueued = []
        self.removed = []
        self.executed = []
        self.execute_all_calls = 0
        self.remove_all_calls = 0
        self.playlist_enqueued = []
        self.task_type_refreshes = 0
        self._task_types = [
            {"value": "generate-md", "label": "Generate Markdown", "description": "Generate markdown summary."},
            {"value": "find_sections", "label": "Find Sections", "description": "Infer song sections."},
        ]

    def task_types(self):
        return list(self._task_types)

    async def refresh_task_types(self):
        self.task_type_refreshes += 1
        return list(self._task_types)

    async def enqueue_item(self, task_type, params):
        self.enqueued.append((task_type, params))
        return {"ok": True, "item_id": "item-1"}

    async def enqueue_full_artifact_playlist(self, params, activate=True):
        self.playlist_enqueued.append((params, activate))
        return {"ok": True, "playlist": {"playlist": "full-artifact-analyzer"}, "scheduled": [{"item_id": "item-1"}], "count": 1}

    async def remove_item(self, item_id):
        self.removed.append(item_id)
        return {"ok": True, "item_id": item_id}

    async def execute_item(self, item_id):
        self.executed.append(item_id)
        return {"ok": True, "item": {"item_id": item_id, "status": "pending"}}

    async def execute_all_queued(self):
        self.execute_all_calls += 1
        return {"item_ids": ["item-1", "item-2"], "count": 2}

    async def remove_all_items(self):
        self.remove_all_calls += 1
        return {"item_ids": ["item-1", "item-2"], "count": 2}


class _FailingAnalyzerService(_AnalyzerService):
    async def enqueue_item(self, task_type, params):
        raise TimeoutError(f"enqueue stalled for {task_type}:{params['filename']}")

    async def execute_item(self, item_id):
        raise TimeoutError(f"execute stalled for {item_id}")

    async def enqueue_full_artifact_playlist(self, params, activate=True):
        raise TimeoutError(f"playlist stalled for {params['filename']}")


class _SongService:
    def __init__(self):
        self.songs_path = "/tmp/songs"
        self.meta_path = "/tmp/meta"

    def list_songs(self):
        return ["alpha-song", "beta-song"]


class _StateManager:
    current_song = type("SongStub", (), {"song_id": "alpha-song"})()


class _Manager:
    def __init__(self, analyzer_service=None):
        self.analyzer_service = analyzer_service or _AnalyzerService()
        self.song_service = _SongService()
        self.state_manager = _StateManager()
        self.events = []

    async def broadcast_event(self, level, message, data=None):
        self.events.append((level, message, data))


@pytest.mark.asyncio
async def test_enqueue_analyzer_item_validates_task_type(monkeypatch):
    monkeypatch.setattr("backend.api.intents.analyzer.actions.helpers.Path.exists", lambda self: True)
    manager = _Manager()

    ok = await enqueue_analyzer_item(manager, {"task_type": "generate-md", "filename": "alpha-song"})

    assert ok is True
    assert manager.analyzer_service.enqueued == [
        (
            "generate-md",
            {"filename": "alpha-song", "song_path": "/tmp/songs/alpha-song.mp3", "meta_path": "/tmp/meta"},
        )
    ]
    assert manager.events[-1] == (
        "info",
        "analyzer_item_enqueued",
        {"task_type": "generate-md", "filename": "alpha-song", "ok": True, "item_id": "item-1"},
    )


@pytest.mark.asyncio
async def test_enqueue_analyzer_item_rejects_unknown_song():
    manager = _Manager()

    ok = await enqueue_analyzer_item(manager, {"task_type": "generate-md", "filename": "missing-song"})

    assert ok is False
    assert manager.events[-1] == (
        "error",
        "analyzer_enqueue_failed",
        {"reason": "unknown_song", "filename": "missing-song", "songs": ["alpha-song", "beta-song"]},
    )


@pytest.mark.asyncio
async def test_enqueue_analyzer_item_handles_service_failure(monkeypatch):
    monkeypatch.setattr("backend.api.intents.analyzer.actions.helpers.Path.exists", lambda self: True)
    manager = _Manager(analyzer_service=_FailingAnalyzerService())

    ok = await enqueue_analyzer_item(manager, {"task_type": "generate-md", "filename": "alpha-song"})

    assert ok is False
    assert manager.events[-1] == (
        "error",
        "analyzer_enqueue_failed",
        {
            "reason": "request_failed",
            "task_type": "generate-md",
            "filename": "alpha-song",
            "error": "enqueue stalled for generate-md:alpha-song",
        },
    )


@pytest.mark.asyncio
async def test_enqueue_analyzer_item_accepts_catalog_task_not_previously_hardcoded(monkeypatch):
    monkeypatch.setattr("backend.api.intents.analyzer.actions.helpers.Path.exists", lambda self: True)
    manager = _Manager()

    ok = await enqueue_analyzer_item(manager, {"task_type": "find_sections", "filename": "alpha-song"})

    assert ok is True
    assert manager.analyzer_service.enqueued == [
        (
            "find_sections",
            {"filename": "alpha-song", "song_path": "/tmp/songs/alpha-song.mp3", "meta_path": "/tmp/meta"},
        )
    ]


@pytest.mark.asyncio
async def test_enqueue_full_artifact_playlist_uses_song_resolution(monkeypatch):
    monkeypatch.setattr("backend.api.intents.analyzer.actions.helpers.Path.exists", lambda self: True)
    manager = _Manager()

    ok = await enqueue_full_artifact_playlist(manager, {"filename": "alpha-song", "activate": True})

    assert ok is True
    assert manager.analyzer_service.playlist_enqueued == [
        (
            {"filename": "alpha-song", "song_path": "/tmp/songs/alpha-song.mp3", "meta_path": "/tmp/meta"},
            True,
        )
    ]
    assert manager.events[-1] == (
        "info",
        "analyzer_playlist_enqueued",
        {
            "playlist": "full-artifact",
            "filename": "alpha-song",
            "activate": True,
            "resolved_playlist": {"playlist": "full-artifact-analyzer"},
            "ok": True,
            "scheduled": [{"item_id": "item-1"}],
            "count": 1,
        },
    )


@pytest.mark.asyncio
async def test_enqueue_full_artifact_playlist_handles_service_failure(monkeypatch):
    monkeypatch.setattr("backend.api.intents.analyzer.actions.helpers.Path.exists", lambda self: True)
    manager = _Manager(analyzer_service=_FailingAnalyzerService())

    ok = await enqueue_full_artifact_playlist(manager, {"filename": "alpha-song"})

    assert ok is False
    assert manager.events[-1] == (
        "error",
        "analyzer_enqueue_failed",
        {"reason": "request_failed", "playlist": "full-artifact", "filename": "alpha-song", "error": "playlist stalled for alpha-song"},
    )


@pytest.mark.asyncio
async def test_remove_and_execute_analyzer_item_emit_events():
    manager = _Manager()

    remove_ok = await remove_analyzer_item(manager, {"item_id": "item-1"})
    execute_ok = await execute_analyzer_item(manager, {"item_id": "item-2"})

    assert remove_ok is True
    assert execute_ok is True
    assert manager.analyzer_service.removed == ["item-1"]
    assert manager.analyzer_service.executed == ["item-2"]
    assert manager.events[-2] == ("info", "analyzer_item_removed", {"item_id": "item-1", "ok": True})
    assert manager.events[-1] == (
        "info",
        "analyzer_item_executed",
        {"item_id": "item-2", "ok": True, "item": {"item_id": "item-2", "status": "pending"}},
    )


@pytest.mark.asyncio
async def test_execute_analyzer_item_handles_service_failure():
    manager = _Manager(analyzer_service=_FailingAnalyzerService())

    ok = await execute_analyzer_item(manager, {"item_id": "item-2"})

    assert ok is False
    assert manager.events[-1] == (
        "error",
        "analyzer_execute_failed",
        {"reason": "request_failed", "item_id": "item-2", "error": "execute stalled for item-2"},
    )


@pytest.mark.asyncio
async def test_execute_all_analyzer_items_returns_patch_when_items_changed():
    manager = _Manager()

    ok = await execute_all_analyzer_items(manager, {})

    assert ok is True
    assert manager.analyzer_service.execute_all_calls == 1
    assert manager.events[-1] == (
        "info",
        "analyzer_items_executed",
        {"item_ids": ["item-1", "item-2"], "count": 2},
    )


@pytest.mark.asyncio
async def test_remove_all_analyzer_items_emits_event():
    manager = _Manager()

    ok = await remove_all_analyzer_items(manager, {})

    assert ok is True
    assert manager.analyzer_service.remove_all_calls == 1
    assert manager.events[-1] == (
        "info",
        "analyzer_items_removed",
        {"item_ids": ["item-1", "item-2"], "count": 2},
    )


def test_analyzer_handlers_map_contains_full_names():
    assert "analyzer.enqueue" in ANALYZER_HANDLERS
    assert "analyzer.enqueue_full_artifact" in ANALYZER_HANDLERS
    assert "analyzer.remove" in ANALYZER_HANDLERS
    assert "analyzer.remove_all" in ANALYZER_HANDLERS
    assert "analyzer.execute" in ANALYZER_HANDLERS
    assert "analyzer.execute_all" in ANALYZER_HANDLERS