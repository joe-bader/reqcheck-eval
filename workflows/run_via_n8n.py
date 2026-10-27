"""Send every requirement through the n8n webhook and write findings.json for eval.score.

    python workflows/run_via_n8n.py --data data/labeled/starter_v1.json --out results/v2-n8n-qwen3-8b-r1
"""
import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent.index import load_requirements  # noqa: E402


def call(url, req_id, text):
    req = urllib.request.Request(url, data=json.dumps({"req_id": req_id, "text": text}).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default="http://localhost:5678/webhook/reqcheck")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    findings, t0 = [], time.time()
    for rid, text in load_requirements(a.data):
        res = call(a.url, rid, text)
        findings += res["findings"]
        print(f"{rid}: {[f['category'] for f in res['findings']]}")
    with open(os.path.join(a.out, "findings.json"), "w") as f:
        json.dump({"findings": findings}, f, indent=2)
    with open(os.path.join(a.out, "meta.json"), "w") as f:
        json.dump({"via": "n8n", "url": a.url, "data": a.data, "wall_seconds": round(time.time() - t0, 1)}, f, indent=2)
    print(f"wrote {a.out} ({round(time.time() - t0, 1)}s)")
