SHELL := /bin/bash

.PHONY: build up down logs fmt lint test ci

build:
	docker compose build --pull

up:
	docker compose up -d

down:
	docker compose down -v

logs:
	docker compose logs -f

fmt:
	@echo "Formatters will be added in a later phase"

lint:
	@echo "Linters will be added in a later phase"

test:
	@echo "Tests will be added in a later phase"

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
