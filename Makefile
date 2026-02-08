.PHONY: redis backend worker up down test

redis:
	docker run -d --name ai-light-redis -p 6379:6379 redis:7

backend:
	PYTHONPATH=./backend $(shell which python3) -m uvicorn backend.main:app --host 0.0.0.0 --port 5001

worker:
	PYTHONPATH=./backend $(shell which celery) -A backend.tasks.celery_app.celery_app worker --loglevel=info

up:
	docker-compose up -d

down:
	docker-compose down

test:
	PYTHONPATH=./backend $(shell which python3) -m pytest -q
