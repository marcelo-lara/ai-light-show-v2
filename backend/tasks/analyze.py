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
        song_path = Path(song_path)
        out_dir = Path(out_dir) if out_dir else Path(os.environ.get('ANALYZER_METADATA_DIR', '/app/metadata'))
        temp_dir = Path(temp_dir) if temp_dir else Path(os.environ.get('ANALYZER_TEMP_DIR', '/app/temp_files'))

        # Prepare redis client for pub/sub notifications (optional)
        rclient = _get_redis_client()

        # Report started
        try:
            self.update_state(state='PROGRESS', meta={'progress': 0, 'detail': 'started'})
        except Exception:
            pass

        # Try importing heavy analyzer modules; if missing (common in docker-compose),
        # fall back to a lightweight stub so the UI/progress plumbing still works.
        try:
            from analyzer.song_analyzer.config import AnalysisConfig
            from analyzer.song_analyzer.pipeline import AnalysisPipeline
            analyzer_available = True
        except Exception as import_exc:
            analyzer_available = False
            import_error = str(import_exc)

        if not analyzer_available:
            out_dir.mkdir(parents=True, exist_ok=True)
            # Minimal metadata schema compatible with backend.models.song.SongMetadata
            metadata = {
                'filename': song_path.stem,
                'length': None,
                'bpm': None,
                'key': None,
                'parts': {},
                'hints': {},
                'drums': {},
            }
            metadata_file = out_dir / f"{song_path.stem}.metadata.json"
            if metadata_file.exists() and not overwrite:
                try:
                    self.update_state(state='SUCCESS', meta={'progress': 100, 'detail': 'already_exists', 'mode': 'stub', 'song': song_path.name})
                except Exception:
                    pass
                return {'status': 'success', 'mode': 'stub', 'song': song_path.name, 'output_dir': str(out_dir)}

            try:
                self.update_state(state='PROGRESS', meta={'progress': 50, 'detail': 'writing_stub_metadata', 'mode': 'stub', 'reason': import_error})
            except Exception:
                pass

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            try:
                self.update_state(state='SUCCESS', meta={'progress': 100, 'detail': 'completed', 'mode': 'stub', 'song': song_path.name})
            except Exception:
                pass

            try:
                if rclient:
                    channel = f"analyze:{self.request.id}"
                    rclient.publish(channel, json.dumps({'type': 'result', 'task_id': self.request.id, 'result': {'song': song_path.name, 'output_dir': str(out_dir), 'mode': 'stub'}}))
            except Exception:
                pass

            return {'status': 'success', 'mode': 'stub', 'song': song_path.name, 'output_dir': str(out_dir)}

        config = AnalysisConfig(
            songs_dir=song_path.parent,
            temp_dir=temp_dir,
            metadata_dir=out_dir,
            device=device,
            stems_model='htdemucs_ft',
            overwrite=overwrite,
        )

        pipeline = AnalysisPipeline(config)

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

        # Run analysis (this may take long) with progress callback
        run_record = pipeline.analyze_song(song_path, progress_callback=_progress_cb)

        # Report completed
        self.update_state(state='SUCCESS', meta={'progress': 100, 'detail': 'completed', 'song': song_path.name, 'mode': 'full'})
        # Publish final result
        try:
            if rclient:
                channel = f"analyze:{self.request.id}"
                rclient.publish(channel, json.dumps({'type': 'result', 'task_id': self.request.id, 'result': {'song': song_path.name, 'output_dir': str(out_dir)}}))
        except Exception:
            pass

        return {'status': 'success', 'mode': 'full', 'song': song_path.name, 'output_dir': str(out_dir)}

    except Exception as exc:
        # Let Celery record the failure with proper exception info.
        # (Updating state to FAILURE with arbitrary meta can break result decoding.)
        try:
            self.update_state(state='PROGRESS', meta={'progress': 0, 'detail': 'failed', 'error': str(exc)})
        except Exception:
            pass
        raise
