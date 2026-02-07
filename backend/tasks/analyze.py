from .celery_app import celery_app
from pathlib import Path
import os
import json


def _get_redis_client():
    try:
        import redis
        broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        return redis.from_url(broker)
    except Exception:
        return None


@celery_app.task(bind=True)
def analyze_song(self, song_path: str, device: str = 'auto', out_dir: str = None, temp_dir: str = None, overwrite: bool = False):
    """Run the analyzer pipeline for a single song.

    This task calls into the existing analyzer code under `/analyzer`.
    It reports start and completion via Celery task meta (PROGRESS state).
    """
    try:
        # Lazy import heavy analyzer modules
        from analyzer.song_analyzer.config import AnalysisConfig
        from analyzer.song_analyzer.pipeline import AnalysisPipeline

        song_path = Path(song_path)
        out_dir = Path(out_dir) if out_dir else Path(os.environ.get('ANALYZER_METADATA_DIR', '/app/metadata'))
        temp_dir = Path(temp_dir) if temp_dir else Path(os.environ.get('ANALYZER_TEMP_DIR', '/app/temp_files'))

        config = AnalysisConfig(
            songs_dir=song_path.parent,
            temp_dir=temp_dir,
            metadata_dir=out_dir,
            device=device,
            stems_model='htdemucs_ft',
            overwrite=overwrite,
        )

        pipeline = AnalysisPipeline(config)

        # Prepare redis client for pub/sub notifications (optional)
        rclient = _get_redis_client()

        # Progress callback
        def _progress_cb(step_run, idx, total):
            try:
                pct = int((idx / total) * 100)
            except Exception:
                pct = 0
            meta = {
                'progress': pct,
                'step': step_run.name,
                'status': step_run.status,
                'index': idx,
                'total': total,
            }
            try:
                self.update_state(state='PROGRESS', meta=meta)
            except Exception:
                pass
            # Publish to redis channel if available
            try:
                if rclient:
                    channel = f"analyze:{self.request.id}"
                    rclient.publish(channel, json.dumps({'type': 'progress', 'task_id': self.request.id, 'meta': meta}))
            except Exception:
                pass

        # Report started
        self.update_state(state='PROGRESS', meta={'progress': 0, 'detail': 'started'})

        # Run analysis (this may take long) with progress callback
        run_record = pipeline.analyze_song(song_path, progress_callback=_progress_cb)

        # Report completed
        self.update_state(state='SUCCESS', meta={'progress': 100, 'detail': 'completed', 'song': song_path.name})
        # Publish final result
        try:
            if rclient:
                channel = f"analyze:{self.request.id}"
                rclient.publish(channel, json.dumps({'type': 'result', 'task_id': self.request.id, 'result': {'song': song_path.name, 'output_dir': str(out_dir)}}))
        except Exception:
            pass

        return {'status': 'success', 'song': song_path.name, 'output_dir': str(out_dir)}

    except Exception as exc:
        # Mark failure
        self.update_state(state='FAILURE', meta={'exc': str(exc)})
        raise
