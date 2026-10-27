# Running it

```bash
for m in nomic-embed-text gemma4:e4b qwen3:8b granite4.2:8b; do ollama pull $m; done
docker run -d -p 6333:6333 qdrant/qdrant
python -m venv .venv && .venv/bin/pip install ollama qdrant-client pydantic

# agent + score
.venv/bin/python -m agent.run --data data/labeled/starter_v1.json --model gemma4:e4b --prompt v2 --out results/my-run
.venv/bin/python -m eval.score --labels data/labeled/starter_v1.json --findings results/my-run/findings.json

# tests, repeat-run summary
.venv/bin/python -m unittest discover -s eval/tests -t .
.venv/bin/python -m eval.summarize --labels data/labeled/starter_v1.json results/run-r1 results/run-r2
```

n8n path (host networking so it reaches Ollama and Qdrant on localhost):

```bash
.venv/bin/python workflows/build_workflow.py --model gemma4:e4b > workflows/reqcheck.json
docker run -d --name n8n --network host -v n8n_data:/home/node/.n8n -v "$PWD/workflows:/workflows:ro" docker.n8n.io/n8nio/n8n
docker exec n8n n8n import:workflow --input=/workflows/reqcheck.json
docker exec n8n n8n list:workflow            # note the ID
docker exec n8n n8n publish:workflow --id=<ID> && docker restart n8n
.venv/bin/python workflows/run_via_n8n.py --data data/labeled/starter_v1.json --out results/my-n8n-run
```

n8n retrieves context from whichever requirements file `agent.run` indexed last.

Layout: `agent/` prompts, schema, retrieval, runner · `eval/` scorer, rules, judge, consistency, tests · `data/` dev set, sealed test set, grading sheets · `workflows/` n8n generator and driver · `results/` one folder per run plus LOG.md.
