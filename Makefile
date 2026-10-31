PYTHON ?= python

.PHONY: setup test lint corpus test-web build-web test-e2e

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"
	-$(PYTHON) -m pre_commit install

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check core corpus tests api benchmarks
	$(PYTHON) -m ruff format --check core corpus tests api benchmarks
	$(PYTHON) -m mypy --strict core

test-web:
	cd web && npm run test

build-web:
	cd web && npm run build

test-e2e:
	$(PYTHON) tests/test_e2e.py

corpus:
	$(PYTHON) -m corpus.build

