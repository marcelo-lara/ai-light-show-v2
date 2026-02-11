from .celery_app import celery_app
from pathlib import Path
import os
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

import json
import time
from typing import List


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
        songs_root = Path(os.environ.get('ANALYZER_SONGS_DIR', '/app/songs'))
        song_path = Path(song_path)
        if not song_path.is_absolute():
            song_path = songs_root / song_path

        out_dir = Path(out_dir) if out_dir else Path(os.environ.get('ANALYZER_METADATA_DIR', '/app/metadata'))
        temp_dir = Path(temp_dir) if temp_dir else Path(os.environ.get('ANALYZER_TEMP_DIR', '/app/temp_files'))

        # Ensure output/temp directories exist even if the host bind mount was recreated
        out_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        if not song_path.exists():
            raise FileNotFoundError(f"Source audio not found: {song_path}")

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
            from song_analyzer.config import AnalysisConfig
            from song_analyzer.pipeline import AnalysisPipeline
            analyzer_available = True
        except Exception as import_exc:
            analyzer_available = False
            import_error = str(import_exc)

        if not analyzer_available:
            out_dir.mkdir(parents=True, exist_ok=True)
            temp_dir.mkdir(parents=True, exist_ok=True)
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
            # Write a stub run log into the temp folder so we have execution breadcrumbs
            log_dir = temp_dir / song_path.stem
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"run_{int(time.time())}.log"
            log_lines = [
                f"[stub] analyze_song called for {song_path.name}",
                f"[stub] analyzer imports unavailable: {import_error}",
                f"[stub] writing minimal metadata to {metadata_file}",
            ]

            if metadata_file.exists() and not overwrite:
                log_lines.append("[stub] metadata already exists; skipping overwrite")
                log_file.write_text("\n".join(log_lines))
                raise RuntimeError("Analyzer unavailable (imports failed); existing metadata left untouched")

            self.update_state(state='PROGRESS', meta={'progress': 50, 'detail': 'writing_stub_metadata', 'mode': 'stub', 'reason': import_error})

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            log_lines.append("[stub] metadata written successfully")
            log_file.write_text("\n".join(log_lines))

            # Fail fast so callers know the full pipeline did not run
            raise RuntimeError("Analyzer unavailable (imports failed); wrote stub metadata only")

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

        # Validate that all steps completed and required artifacts exist
        self.update_state(state='PROGRESS', meta={'progress': 99, 'detail': 'validating', 'song': song_path.name, 'mode': 'full'})
        _validate_full_run(run_record, out_dir)

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


def _validate_full_run(run_record, metadata_root: Path):
    """Validate that all steps succeeded and artifacts exist.

    Raises RuntimeError if any step failed or any expected artifact is missing.
    """
    song_slug = run_record.song.get('song_slug') or run_record.song.get('filename')
    if not song_slug:
        raise RuntimeError('Missing song_slug in run record')

    base = metadata_root / song_slug
    expected_files: List[Path] = []

    # Analysis JSON artifacts
    analysis = base / 'analysis'
    expected_files.extend([
        analysis / 'run.json',
        analysis / 'timeline.json',
        analysis / 'stems.json',
        analysis / 'beats.json',
        analysis / 'energy.json',
        analysis / 'onsets.json',
        analysis / 'vocals.json',
        analysis / 'sections.json',
        analysis / 'patterns.json',
    ])

    # Plots
    plots = base / 'plots'
    expected_files.extend([
        plots / 'beats.svg',
        plots / 'energy.svg',
        plots / 'sections.svg',
        plots / 'vocals.svg',
        plots / 'drums.svg',
        plots / 'bass.svg',
        plots / 'other.svg',
    ])

    # Show plan
    show_plan = base / 'show_plan'
    expected_files.extend([
        show_plan / 'roles.json',
        show_plan / 'moments.json',
        show_plan / 'show_plan.json',
    ])

    missing = [str(p) for p in expected_files if not p.exists()]

    failed_steps = [s.name for s in run_record.steps if getattr(s, 'status', '') != 'ok' or getattr(s, 'failure', None)]

    if failed_steps or missing:
        problems = []
        if failed_steps:
            problems.append(f"failed steps: {', '.join(failed_steps)}")
        if missing:
            problems.append(f"missing artifacts: {', '.join(missing)}")
        raise RuntimeError("Validation failed: " + '; '.join(problems))
