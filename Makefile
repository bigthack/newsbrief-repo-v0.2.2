SHELL := /bin/bash

.PHONY: up down fmt lint type test seed openapi

up:
	docker compose up -d --build

down:
	docker compose down

fmt:
	black .

lint:
	ruff check .
	bandit -q -r api core ingestion nlp emailer personalization data || true

type:
	mypy .

test:
	pytest -q

seed:
	python scripts/seed.py

openapi:
	python scripts/validate_openapi.py docs/openapi.yaml


demo:
	python scripts/demo.py --topic "$(TOPIC)" --limit "$(LIMIT)" --date "$(DATE)" --format "$(FORMAT)" --outdir "$(OUTDIR)"



validate:
	python scripts/validate_manifest.py


pages:
	python scripts/build_pages_index.py
	python scripts/build_feeds.py --base-url "$${BASE_URL:-http://localhost:8000}" --public-dir public



serve:
	cd public && python -m http.server 8000

