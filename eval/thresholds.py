"""Score a System 1 run's probabilities: threshold sweep, average precision and calibration.

    python -m eval.thresholds --labels data/labeled/starter_v1.json --probs results/s1-kev9b-r1/probs.json
    python -m eval.thresholds --labels data/labeled/test_synthetic_v1.json --probs ... --threshold 0.35

Without --threshold it sweeps and reports the F1-best threshold (do this on the dev set only).
With --threshold it scores that fixed threshold (use this on the test set).
"""
import argparse
import json

from eval.score import CATEGORIES, load_truth, score


def pairs(truth, probs):
    """[(probability, is_gold)] over every (req_id, category) pair."""
    return [(row[c], c in truth[row["req_id"]]) for row in probs for c in CATEGORIES]


def predicted(probs, t):
    return {(row["req_id"], c) for row in probs for c in CATEGORIES if row[c] >= t}


def average_precision(items):
    """Area under the precision-recall curve, computed as mean precision at each gold item's rank."""
    ranked = sorted(items, key=lambda x: -x[0])
    n_gold = sum(g for _, g in ranked)
    hits, total = 0, 0.0
    for i, (_, g) in enumerate(ranked, start=1):
        if g:
            hits += 1
            total += hits / i
    return total / n_gold if n_gold else None


def brier(items):
    """Mean squared gap between the stated probability and what happened (0 is perfect, 0.25 is a coin flip)."""
    return sum((p - g) ** 2 for p, g in items) / len(items)


def calibration_table(items, bins=(0, 0.2, 0.4, 0.6, 0.8, 1.0001)):
    rows = []
    for lo, hi in zip(bins, bins[1:]):
        b = [(p, g) for p, g in items if lo <= p < hi]
        if b:
            rows.append((lo, min(hi, 1.0), len(b), sum(p for p, _ in b) / len(b), sum(g for _, g in b) / len(b)))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--probs", required=True)
    ap.add_argument("--threshold", type=float, help="score this fixed threshold instead of sweeping")
    args = ap.parse_args(argv)
    truth = load_truth(args.labels)
    probs = json.load(open(args.probs))
    items = pairs(truth, probs)

    print(f"average precision {average_precision(items):.3f}  Brier {brier(items):.3f}  "
          f"(flag-everything precision {sum(g for _, g in items) / len(items):.3f})")
    for c in CATEGORIES:
        ci = [(row[c], c in truth[row["req_id"]]) for row in probs]
        ap_c = average_precision(ci)
        print(f"  {c}: average precision {ap_c if ap_c is None else round(ap_c, 3)}  Brier {brier(ci):.3f}")
    print("calibration (stated vs. actual):")
    for lo, hi, n, mean_p, rate in calibration_table(items):
        print(f"  p {lo:.1f}-{hi:.1f}: n={n:3}  stated {mean_p:.2f}  actual {rate:.2f}")

    if args.threshold is None:
        best = None
        for t in [i / 100 for i in range(5, 100, 5)]:
            r = score(truth, predicted(probs, t))["overall"]
            f1 = r["f1"] or 0
            print(f"  t={t:.2f}  P {r['precision'] if r['precision'] is None else round(r['precision'], 3)}  "
                  f"R {r['recall']:.3f}  F1 {f1:.3f}")
            if best is None or f1 > best[1]:
                best = (t, f1)
        print(f"best threshold on this set: {best[0]:.2f} (F1 {best[1]:.3f})")
    else:
        r = score(truth, predicted(probs, args.threshold))
        for name in ("overall", *CATEGORIES):
            m = r[name]
            print(f"{name:8} TP {m['tp']:3} FP {m['fp']:3} FN {m['fn']:3}  F1 {m['f1'] if m['f1'] is None else round(m['f1'], 3)}")


if __name__ == "__main__":
    main()
