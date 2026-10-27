"""Summarize repeated runs: mean and spread of overall and per-category F1.

    python -m eval.summarize --labels data/labeled/starter_v1.json results/runA-r1 results/runA-r2 ...
"""
import argparse
import statistics as st

from eval.score import CATEGORIES, load_predictions, load_truth, score


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("runs", nargs="+", help="run folders containing findings.json")
    args = ap.parse_args(argv)
    truth = load_truth(args.labels)
    rows = [score(truth, load_predictions(f"{r}/findings.json")) for r in args.runs]
    print(f"n={len(rows)} runs")
    for name in ("overall", *CATEGORIES):
        for metric in ("precision", "recall", "f1"):
            vals = [r[name][metric] for r in rows if r[name][metric] is not None]
            if vals:
                sd = st.stdev(vals) if len(vals) > 1 else 0.0
                print(f"{name:8}{metric:10} mean {st.mean(vals):.3f}  sd {sd:.3f}  range {min(vals):.3f}-{max(vals):.3f}")


if __name__ == "__main__":
    main()
