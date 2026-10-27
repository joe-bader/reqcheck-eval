#!/bin/bash
cd /home/joe/Projects/reqcheck-eval
for r in 1 2 3; do
  .venv/bin/python -u -m agent.run --data data/labeled/starter_v1.json --prompt v2 --model qwen3.6:35b-a3b --out results/v2-qwen36-35b-a3b-k3-r$r > results/logs/v2-qwen36-r$r.log 2>&1
done
.venv/bin/python -u -m agent.run --data data/labeled/test_synthetic_v1.json --prompt v2 --model qwen3.6:35b-a3b --out results/test-v2-qwen36-35b-a3b-k3-r1 > results/logs/test-v2-qwen36-r1.log 2>&1
echo all-done > results/logs/qwen36.done
