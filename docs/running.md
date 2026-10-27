# Running it

Prerequisites: [Ollama](https://ollama.com/download) running on the host, Docker, and Python 3.

```bash
make demo
```

This starts Qdrant (or reuses one already on port 6333), creates `.venv` from `requirements.txt`, pulls `gemma4:e4b` and `nomic-embed-text`, runs the agent on the dev set, and prints the score. Expect dev F1 0.595 for the default model.

Other targets:

| Command | What it does |
|---|---|
| `make demo MODEL=qwen3:8b` | Same, with a different Ollama model |
| `make test` | Unit tests for the scorer and metrics |
| `make n8n` | The same pipeline through an n8n workflow (Docker, host networking) |

Running pieces directly:

```bash
.venv/bin/python -m agent.run --data data/labeled/starter_v1.json --model gemma4:e4b --prompt v2 --out results/my-run
.venv/bin/python -m eval.score --labels data/labeled/starter_v1.json --findings results/my-run/findings.json
.venv/bin/python -m agent.system1 --data data/labeled/starter_v1.json --model kev:9b-q4_K_M --out results/my-kev-run
.venv/bin/python -m eval.thresholds --labels data/labeled/starter_v1.json --probs results/my-kev-run/probs.json
.venv/bin/python -m eval.summarize --labels data/labeled/starter_v1.json results/run-r1 results/run-r2
```

Layout: `agent/` prompts, schema, retrieval, runners · `eval/` scorer, rules, judge, thresholds, tests · `data/` dev set, sealed test set, grading sheets · `workflows/` n8n generator and driver · `results/` one folder per run plus LOG.md.
