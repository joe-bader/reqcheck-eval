# One-command setup and demo. Prerequisites: Ollama running on the host, Docker.
PY := .venv/bin/python
MODEL ?= gemma4:e4b
DATA ?= data/labeled/starter_v1.json
OUT ?= results/demo

.PHONY: demo setup check qdrant models test n8n

demo: setup  ## run the agent on the dev set and score it
	$(PY) -m agent.run --data $(DATA) --model $(MODEL) --prompt v2 --out $(OUT)
	$(PY) -m eval.score --labels $(DATA) --findings $(OUT)/findings.json

setup: check .venv qdrant models

check:
	@command -v ollama >/dev/null || { echo "Ollama is required: https://ollama.com/download"; exit 1; }
	@curl -sf localhost:11434/api/version >/dev/null || { echo "Ollama is installed but not running (try: ollama serve)"; exit 1; }
	@command -v docker >/dev/null || { echo "Docker is required for Qdrant"; exit 1; }

.venv: requirements.txt
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt
	@touch .venv

qdrant:  # reuse a Qdrant already listening on 6333, otherwise start one
	@curl -sf localhost:6333/healthz >/dev/null || docker compose up -d --wait qdrant

models:
	ollama pull nomic-embed-text
	ollama pull $(MODEL)

test: .venv
	$(PY) -m unittest discover -s eval/tests -t .

n8n: setup  ## run the same pipeline through n8n
	$(PY) workflows/build_workflow.py --model $(MODEL) > workflows/reqcheck.json
	docker compose --profile n8n up -d n8n
	@until curl -sf localhost:5678/healthz >/dev/null; do sleep 2; done
	docker compose exec n8n n8n import:workflow --input=/workflows/reqcheck.json
	docker compose exec n8n sh -c 'n8n publish:workflow --id=$$(n8n list:workflow | grep reqcheck | cut -d"|" -f1)'
	docker compose restart n8n
	@until curl -sf localhost:5678/healthz >/dev/null; do sleep 2; done
	$(PY) workflows/run_via_n8n.py --data $(DATA) --out $(OUT)-n8n
