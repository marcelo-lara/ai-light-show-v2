Analyzer + Worker README
=========================

This documents how to run the analyzer worker and Celery tasks locally.

Prerequisites
-------------
- Use the `ai-light` Python environment as requested. Install backend deps:

```bash
pip install -r backend/requirements.txt
```

Running locally
---------------
1. Start Redis (detached):

```bash
docker run -d --name ai-light-redis -p 6379:6379 redis:7
```

2. Start the backend API:

```bash
PYTHONPATH=./backend python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 5001
```

3. Start the Celery worker (in the same ai-light env):

```bash
PYTHONPATH=./backend celery -A backend.tasks.celery_app.celery_app worker --loglevel=info
```

Developer note
--------------
- Tests use Celery's `task_always_eager` mode to run tasks synchronously so CI/dev machines don't need Redis.
- The analyzer is heavy (GPU models). Integration tests in this repo mock the analyzer pipeline to keep tests fast.
