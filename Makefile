.PHONY: up down test test-sweep test-live test-browser

up:
	docker-compose up -d

down:
	docker-compose down

test:
	PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q

test-sweep:
	PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q tests/test_dmx_canvas_render.py -k sweep

test-live:
	PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q
	docker compose down && docker compose up --build -d

test-browser:
	DMX_NODE_IP=dmx-node docker compose up -d dmx-node frontend backend
	DMX_NODE_IP=dmx-node docker compose run --rm browser-tests
