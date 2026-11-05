# Linux/CI convenience commands. Windows uses scripts/dev.ps1.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
PY ?= python3
VENV ?= .venv
BIN := $(abspath $(VENV))/bin
TAG ?= $(shell git rev-parse HEAD)
REGISTRY ?=
CONTEXT ?= rahbar
API ?= http://127.0.0.1:8085
HOST ?= rahbar.local

.PHONY: help install tools test lint manifests dev cluster images apply index fetch eval eval-fixtures check
help:
	@echo "install tools test lint manifests dev cluster images apply index fetch eval eval-fixtures check"
install:
	$(PY) -m venv $(VENV)
	$(BIN)/python -m pip install -r api/requirements-dev.txt -r indexer/requirements-dev.txt
tools:
	$(BIN)/python scripts/bootstrap_tools.py kind kubeconform trivy actionlint --manifests
test:
	cd api && $(BIN)/python -m pytest -q
	cd indexer && $(BIN)/python -m pytest -q
	$(BIN)/python -m pytest -q eval/tests scripts/tests
	node scripts/ui.test.cjs
lint:
	$(BIN)/python -m ruff check api indexer eval corpus scripts
	cd api && $(BIN)/python -m mypy app
	cd indexer && $(BIN)/python -m mypy pipeline
manifests:
	$(BIN)/python scripts/check_platform.py
	for overlay in dev prod ci; do kubectl kustomize k8s/overlays/$$overlay | kubeconform -strict -summary -kubernetes-version 1.35.0; done
dev:
	cd api && SERVE_UI_DIR=../ui RETRIEVER=stub LLM_PROVIDER=stub $(BIN)/uvicorn app.main:app --host 127.0.0.1 --port 8000
cluster:
	minikube start -p rahbar --driver=docker --cni=calico --memory=6144 --cpus=4 --keep-context --kubernetes-version=v1.37.0
	minikube addons enable metrics-server -p rahbar
	minikube addons enable ingress -p rahbar
images:
	for image in api indexer ui; do docker build -t rahbar-$$image:$(TAG) $$image; minikube image load -p rahbar rahbar-$$image:$(TAG); done
apply:
	$(BIN)/python scripts/deploy.py apply --overlay dev --context $(CONTEXT) --tag $(TAG) --registry="$(REGISTRY)"
index:
	kubectl --context $(CONTEXT) -n rahbar create job --from=cronjob/reindex manual-reindex-$$(date +%s)
fetch:
	$(BIN)/python scripts/fetch_snapshot.py --sources corpus/sources.yaml --manifest corpus/MANIFEST.md --out corpus/raw
eval:
	$(BIN)/python eval/run_eval.py --api $(API) --host $(HOST) --golden eval/golden.yaml --baseline eval/baseline.json --out .venv/real-results.json --bypass-cache
eval-fixtures:
	$(BIN)/python eval/run_eval.py --api http://127.0.0.1:18080 --host $(HOST) --golden eval/fixtures/golden.fixture.yaml --baseline eval/fixtures/baseline.json --out .venv/fixture-results.json --bypass-cache
check:
	$(BIN)/python scripts/check_submission.py
