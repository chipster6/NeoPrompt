SHELL := /bin/bash

.PHONY: build up down logs fmt lint typecheck test ci

build:
	docker compose build --pull

up:
	docker compose up -d

down:
	docker compose down -v

logs:
	docker compose logs -f

# Format code (best-effort, non-fatal)
fmt:
	-ruff check backend --fix || true
	-cd frontend && npx eslint . --fix || true

# Lint code
lint:
	ruff check backend
	cd frontend && npx eslint .

# Typecheck (Python + TypeScript)
typecheck:
	mypy -p backend
	cd frontend && npx tsc --noEmit

# Run tests (backend + frontend)
# Backend: prefer pytest in virtualenv; fallback to python -m pytest
# Frontend: prefer test:ci if present; otherwise run tests once
test:
	pytest -q tests/backend || python -m pytest -q tests/backend
	cd frontend && (npm run | grep -q "test:ci" && npm run test:ci || npm test -- --run)

ci: build
	@echo "Local CI stub: images built"

.PHONY: cli
cli:
	NEOPROMPT_API_BASE?=http://localhost/api scripts/neoprompt $(args)

.PHONY: sdk-python-install
sdk-python-install:
	pip install -e sdk/python/neoprompt

.PHONY: sdk-ts-build
sdk-ts-build:
	cd sdk/typescript && npm ci && npm run build
