import os
from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)

celery_app = Celery("ai_light_show", broker=BROKER_URL, backend=RESULT_BACKEND)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Allow forcing task module imports via env var (comma-separated)
_imports = os.environ.get('CELERY_IMPORTS')
if _imports:
    celery_app.conf.update(imports=[p.strip() for p in _imports.split(',') if p.strip()])
