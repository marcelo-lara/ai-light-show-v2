from backend.tasks.celery_app import celery_app
try:
    from backend.tasks.analyze import analyze_song
except Exception:
    analyze_song = None


def test_celery_and_task_import():
    assert celery_app is not None
    assert analyze_song is not None
    # task should expose apply_async or delay
    assert hasattr(analyze_song, 'apply_async') or hasattr(analyze_song, 'delay')
