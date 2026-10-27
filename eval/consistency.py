"""Labeler self-consistency: re-label a random sample blind, then compare with the original labels.

    python -m eval.consistency sheet   --labels data/labeled/starter_v1.json --n 10 --out data/calibration/relabel_sheet.json
    python -m eval.consistency compare --labels data/labeled/starter_v1.json --sheet data/calibration/relabel_sheet.json

The sheet holds requirement text only, with "labels": null. Fill in labels in the same format as the labeled
file ([] for clean). Comparison is over (req_id, category) decisions: 3 per requirement, flagged or not.
"""
import argparse
import json
import random

from eval.judge import cohen_kappa
from eval.score import CATEGORIES, load_truth


def make_sheet(labels, n, out, seed):
    reqs = json.load(open(labels))["requirements"]
    sample = random.Random(seed).sample(reqs, n)
    sheet = {"note": "Re-label blind, without opening the original file. Use eval/labeling-rules.md. [] means clean.",
             "source": labels, "seed": seed,
             "requirements": [{"req_id": r["req_id"], "text": r["text"], "labels": None} for r in sample]}
    json.dump(sheet, open(out, "w"), indent=2)
    print(f"wrote {n} requirements to {out}")


def compare(labels, sheet):
    first = load_truth(labels)
    second = load_truth(sheet)  # refuses the sheet if any labels are still null
    a, b, diffs = [], [], []
    for rid in sorted(second):
        for c in CATEGORIES:
            x, y = c in first[rid], c in second[rid]
            a.append(x)
            b.append(y)
            if x != y:
                diffs.append(f"{rid} {c}: first {'yes' if x else 'no'}, now {'yes' if y else 'no'}")
    agree = sum(x == y for x, y in zip(a, b)) / len(a)
    k = cohen_kappa(a, b)
    same_req = sum(first[r] == second[r] for r in second)
    print(f"{len(second)} requirements, {len(a)} decisions")
    print(f"decision agreement {agree:.2f}  Cohen's kappa {k if k is None else round(k, 2)}  "
          f"requirements labeled identically {same_req}/{len(second)}")
    for d in diffs:
        print("  ", d)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet"); s.add_argument("--labels", required=True); s.add_argument("--n", type=int, default=10)
    s.add_argument("--out", required=True); s.add_argument("--seed", type=int, default=7)
    c = sub.add_parser("compare"); c.add_argument("--labels", required=True); c.add_argument("--sheet", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "sheet":
        make_sheet(args.labels, args.n, args.out, args.seed)
    else:
        compare(args.labels, args.sheet)


if __name__ == "__main__":
    main()
