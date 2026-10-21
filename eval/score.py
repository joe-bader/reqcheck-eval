"""Score agent findings against hand-labeled ground truth.

Unit of scoring: the (req_id, category) pair. See eval/matching.md.

    python -m eval.score --labels data/labeled/starter_v1.json --findings results/run1/findings.json
"""
import argparse
import json
import sys

CATEGORIES = ("AMB", "UNT", "GAP")


class LabelError(ValueError):
    pass


def load_truth(path):
    """Return {req_id: set of categories}. Refuses unlabeled (null) or malformed entries."""
    with open(path) as f:
        data = json.load(f)
    truth = {}
    for req in data["requirements"]:
        rid = req["req_id"]
        if rid in truth:
            raise LabelError(f"duplicate req_id {rid}")
        if req.get("labels") is None:
            raise LabelError(f"{rid} is unlabeled (labels is null)")
        if not isinstance(req["labels"], list):
            raise LabelError(f"{rid}: labels must be a list")
        cats = set()
        for lab in req["labels"]:
            if lab.get("category") not in CATEGORIES:
                raise LabelError(f"{rid}: bad category {lab.get('category')!r}")
            cats.add(lab["category"])
        truth[rid] = cats
    return truth


def load_predictions(path):
    """Return set of (req_id, category) pairs. Duplicate findings collapse to one pair."""
    with open(path) as f:
        data = json.load(f)
    findings = data["findings"] if isinstance(data, dict) else data
    return {(f["req_id"], f["category"]) for f in findings}


def prf(tp, fp, fn):
    """Precision, recall, F1. An empty denominator gives None for precision/recall. F1 is 0.0 unless there are no pairs at all."""
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    # Same as 2PR/(P+R) but defined whenever there is anything to get wrong; only n/a if there are no pairs at all.
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None
    return p, r, f1


def score(truth, predicted):
    """Compare truth {req_id: set(cats)} with predicted {(req_id, cat)}; return a metrics dict."""
    gold = {(rid, c) for rid, cats in truth.items() for c in cats}
    unknown = sorted(p for p in predicted if p[0] not in truth)
    bad_cat = sorted(p for p in predicted if p[1] not in CATEGORIES)
    # Predictions about unknown ids or categories can never match, so they count as false positives.
    result = {"unknown_req_ids": unknown, "unknown_categories": bad_cat}
    groups = {"overall": (gold, predicted)}
    for c in CATEGORIES:
        groups[c] = ({g for g in gold if g[1] == c}, {p for p in predicted if p[1] == c})
    for name, (g, p) in groups.items():
        tp, fp, fn = len(g & p), len(p - g), len(g - p)
        pr, rc, f1 = prf(tp, fp, fn)
        result[name] = {"tp": tp, "fp": fp, "fn": fn, "precision": pr, "recall": rc, "f1": f1}
    return result


def _fmt(x):
    return "  n/a" if x is None else f"{x:.3f}"


def format_report(result):
    lines = [f"{'':8}{'TP':>4}{'FP':>4}{'FN':>4}{'P':>7}{'R':>7}{'F1':>7}"]
    for name in ("overall", *CATEGORIES):
        m = result[name]
        lines.append(f"{name:8}{m['tp']:>4}{m['fp']:>4}{m['fn']:>4}"
                     f"{_fmt(m['precision']):>7}{_fmt(m['recall']):>7}{_fmt(m['f1']):>7}")
    if result["unknown_req_ids"]:
        lines.append(f"WARNING: findings for unknown req_ids (counted as FP): {result['unknown_req_ids']}")
    if result["unknown_categories"]:
        lines.append(f"WARNING: findings with unknown categories (counted as FP): {result['unknown_categories']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--findings", required=True)
    ap.add_argument("--json", action="store_true", help="print raw metrics as JSON")
    args = ap.parse_args(argv)
    try:
        truth = load_truth(args.labels)
    except LabelError as e:
        sys.exit(f"refusing to score: {e}")
    result = score(truth, load_predictions(args.findings))
    print(json.dumps(result, indent=2) if args.json else format_report(result))


if __name__ == "__main__":
    main()
