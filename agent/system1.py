"""Run a System 1 decision model (e.g. Kev) over a requirements file.

System 1 models don't generate text. Each requirement becomes a `state`, each defect category a yes/no
(`noul`) question, and the model returns a calibrated probability per question in one forward pass.
So there is no evidence quote and no suggested fix, and no temperature or seed.

    python -m agent.system1 --data data/labeled/starter_v1.json --model kev:9b-q4_K_M --out results/s1-kev9b-r1

Writes probs.json (all probabilities), findings.json (pairs at or above --threshold, for eval.score) and meta.json.
Pick the threshold on the dev set with eval.thresholds, then freeze it for the test set.
"""
import argparse
import json
import os
import time

import ollama
from qdrant_client import QdrantClient

from agent.index import QDRANT_URL, build_index, load_requirements, related

COLLECTION = "requirements_v1"

# Condensed from eval/labeling-rules.md. Questions are answered independently, so the rules' precedence
# between categories ("one span, one label") can't be enforced by the model.
QUESTIONS = {
    "AMB": {
        "type": "noul",
        "instructions": "Does the requirement name something measurable (time, size, count, frequency) but leave its value, "
                        "list or definition vague or missing, so two testers could check for different things?",
        "criteria": {
            "true": "A measurable property has a vague or missing value, e.g. 'promptly', 'large', 'several', 'as needed'.",
            "false": "Every measurable property has a concrete value, or none is named.",
        },
    },
    "UNT": {
        "type": "noul",
        "instructions": "Is the requirement untestable: a subjective quality, an unbounded absolute, or an obligation with no "
                        "observable outcome, so no test with one definite expected result can be written?",
        "criteria": {
            "true": "It relies on a subjective quality (e.g. intuitive, seamless, robust) or an absolute (always, never).",
            "false": "A tester could write a test with one definite pass/fail result.",
        },
    },
    "GAP": {
        "type": "noul",
        "instructions": "Is information a tester needs absent (not merely vague): a term, document or standard that is not "
                        "defined in the related requirements, a missing trigger or condition, missing failure behavior, "
                        "or a missing actor? A term counts as defined if a related requirement defines it.",
        "criteria": {
            "true": "A tester would have to ask what X is, what happens when Y, or who does Z.",
            "false": "Nothing a tester needs is missing.",
        },
    },
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", default="kev:9b-q4_K_M")
    ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, default=3, help="related requirements to include in the state")
    ap.add_argument("--threshold", type=float, default=0.5, help="flag a category when its probability is at or above this")
    ap.add_argument("--limit", type=int, help="only the first N requirements (plumbing checks)")
    args = ap.parse_args(argv)

    reqs = load_requirements(args.data)[: args.limit]
    client = QdrantClient(url=QDRANT_URL)
    build_index(client, COLLECTION, load_requirements(args.data))

    os.makedirs(args.out, exist_ok=True)
    probs, findings = [], []
    t0 = time.time()
    for rid, text in reqs:
        ctx = related(client, COLLECTION, rid, text, args.k)
        state = {"requirement": f"{rid}: {text}", "related_requirements": [f"{c}: {t}" for c, t in ctx]}
        t1 = time.time()
        resp = ollama.systemone(model=args.model, state=state, questions=QUESTIONS)
        row = {"req_id": rid, "seconds": round(time.time() - t1, 3), "context": [c for c, _ in ctx]}
        for cat in QUESTIONS:
            p = resp.answers[cat].noul
            row[cat] = p
            if p >= args.threshold:
                findings.append({"req_id": rid, "category": cat, "probability": p})
        probs.append(row)
        print(f"{rid}: " + "  ".join(f"{c} {row[c]:.2f}" for c in QUESTIONS))

    ps = [m for m in ollama.ps().models if m.model == args.model]
    meta = {**vars(args), "kind": "system1", "n_requirements": len(reqs), "wall_seconds": round(time.time() - t0, 1),
            "gpu_fraction": (ps[0].size_vram / ps[0].size) if ps and ps[0].size else None}
    for name, obj in (("probs.json", probs), ("findings.json", {"findings": findings}), ("meta.json", meta)):
        with open(os.path.join(args.out, name), "w") as f:
            json.dump(obj, f, indent=2)
    print(f"wrote {args.out}  ({meta['wall_seconds']}s, gpu_fraction={meta['gpu_fraction']})")


if __name__ == "__main__":
    main()
