"""Run the reviewer over a requirements file and write findings for eval.score.

    python -m agent.run --data data/labeled/starter_v1.json --model qwen3:8b --prompt v0 --out results/v0-qwen3-8b-r1
"""
import argparse
import json
import os
import time

import ollama
from qdrant_client import QdrantClient

from agent.index import QDRANT_URL, build_index, load_requirements, related
from agent.prompts import PROMPTS
from agent.schema import Review, ReviewV1

COLLECTION = "requirements_v1"
SCHEMAS = {"v0": Review, "v1": ReviewV1}


def review_one(schema, model, system, user, num_ctx, temperature, seed, think):
    resp = ollama.chat(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        format=schema.model_json_schema(),
        think=think,
        options={"temperature": temperature, "seed": seed, "num_ctx": num_ctx},
    )
    return schema.model_validate_json(resp.message.content), resp


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--prompt", default="v0", choices=PROMPTS)
    ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, default=3, help="related requirements to retrieve")
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--think", action="store_true", help="let the model reason first (slower)")
    ap.add_argument("--limit", type=int, help="only the first N requirements (plumbing checks)")
    args = ap.parse_args(argv)

    reqs = load_requirements(args.data)[: args.limit]
    client = QdrantClient(url=QDRANT_URL)
    build_index(client, COLLECTION, load_requirements(args.data))
    system, make_user = PROMPTS[args.prompt]

    os.makedirs(args.out, exist_ok=True)
    findings, raw, inconsistent = [], [], 0
    t0 = time.time()
    for rid, text in reqs:
        ctx = related(client, COLLECTION, rid, text, args.k)
        review, resp = review_one(SCHEMAS[args.prompt], args.model, system, make_user(rid, text, ctx), args.num_ctx,
                                  args.temperature, args.seed, args.think)
        verdict = getattr(review, "verdict", "defective" if review.findings else "clean")
        if (verdict == "clean") != (not review.findings):
            inconsistent += 1  # verdict disagrees with findings; findings are what get scored
        findings += [{"req_id": rid, **f.model_dump()} for f in review.findings]
        raw.append({"req_id": rid, "verdict": verdict, "analysis": getattr(review, "analysis", None), "n_findings": len(review.findings),
                    "context": [c[0] for c in ctx], "prompt_tokens": resp.prompt_eval_count,
                    "seconds": (resp.total_duration or 0) / 1e9})
        print(f"{rid}: {verdict:9} {[f.category for f in review.findings]}")

    ps = [m for m in ollama.ps().models if m.model == args.model]
    meta = {**vars(args), "n_requirements": len(reqs), "wall_seconds": round(time.time() - t0, 1),
            "verdict_findings_mismatch": inconsistent,
            "gpu_fraction": (ps[0].size_vram / ps[0].size) if ps and ps[0].size else None}
    for name, obj in (("findings.json", {"findings": findings}), ("per_requirement.json", raw), ("meta.json", meta)):
        with open(os.path.join(args.out, name), "w") as f:
            json.dump(obj, f, indent=2)
    print(f"wrote {args.out}  ({meta['wall_seconds']}s, gpu_fraction={meta['gpu_fraction']})")


if __name__ == "__main__":
    main()
