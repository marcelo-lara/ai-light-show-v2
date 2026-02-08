import sys
import types
from types import ModuleType
from backend.tasks.analyze import analyze_song, celery_app


def test_analyze_task_runs_with_mocked_pipeline(tmp_path, monkeypatch):
    # Create fake analyzer.song_analyzer.config module
    cfg_mod = ModuleType('analyzer.song_analyzer.config')
    def AnalysisConfig(**kwargs):
        return kwargs
    cfg_mod.AnalysisConfig = AnalysisConfig

    # Create fake pipeline module with AnalysisPipeline
    pipeline_mod = ModuleType('analyzer.song_analyzer.pipeline')

    class FakePipeline:
        def __init__(self, config):
            self.config = config

        def analyze_song(self, song_path, progress_callback=None):
            # Simulate a single step and call progress callback
            class StepRun:
                name = 'mock_step'
                status = 'ok'

            if progress_callback:
                progress_callback(StepRun(), 1, 1)
            return None

    pipeline_mod.AnalysisPipeline = FakePipeline

    # Inject into sys.modules so backend.tasks.analyze imports succeed
    sys.modules['analyzer.song_analyzer.config'] = cfg_mod
    sys.modules['analyzer.song_analyzer.pipeline'] = pipeline_mod

    # Run the task synchronously and use in-memory result backend to avoid Redis
    celery_app.conf.task_always_eager = True
    celery_app.conf.result_backend = 'cache+memory://'
    celery_app.conf.broker_url = 'memory://'

    result = analyze_song.apply(args=[str(tmp_path / 'song.mp3')])
    assert result is not None
    retval = result.get(timeout=10)
    assert retval.get('status') == 'success'
