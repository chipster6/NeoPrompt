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
