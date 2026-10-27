"""LLM-as-judge for the quality of suggested fixes, plus calibration against human grades.

    python -m eval.judge sheet  --labels L.json --run RUN_DIR --n 20 --out data/calibration/fix_sheet.json
    python -m eval.judge judge  --sheet data/calibration/fix_sheet.json --model gemma4:e4b
    python -m eval.judge agree  --sheet data/calibration/fix_sheet.json

`sheet` samples findings that are true positives (the fix is for a real defect) and leaves human_grade blank.
The human grades WITHOUT seeing judge_grade; `judge` fills judge_grade in a separate step; `agree` compares them.
Grade scale: 1 = wrong or unusable, 2 = right direction but vague or incomplete, 3 = concrete, correct, testable.
"""
import argparse
import json
import random
from collections import Counter

import ollama
from pydantic import BaseModel

from eval.score import load_truth

RUBRIC = """You grade suggested fixes for defective software requirements.
Scale:
1 = wrong or unusable (does not address the defect, introduces new problems, or just restates the requirement)
2 = right direction but vague or incomplete (names the problem, but a tester could still not write a definite pass/fail check)
3 = concrete, correct and testable (specific value, definition, actor or condition that resolves the defect)
Judge only the fix, against the defect category and quoted evidence."""


class Grade(BaseModel):
    reason: str
    grade: int  # 1, 2 or 3; reason comes first so the judge explains before scoring


def make_sheet(labels, run, n, out, seed):
    truth = load_truth(labels)
    texts = {r["req_id"]: r["text"] for r in json.load(open(labels))["requirements"]}
    findings = json.load(open(f"{run}/findings.json"))["findings"]
    seen, tps = set(), []
    for f in findings:
        key = (f["req_id"], f["category"])
        if f["category"] in truth.get(f["req_id"], set()) and key not in seen:
            seen.add(key)
            tps.append(f)
    random.Random(seed).shuffle(tps)
    items = [{"id": i, "req_id": f["req_id"], "requirement": texts[f["req_id"]], "category": f["category"],
              "evidence": f["evidence"], "suggested_fix": f["suggested_fix"], "human_grade": None, "judge_grade": None}
             for i, f in enumerate(tps[:n])]
    json.dump({"scale": RUBRIC, "source_run": run, "items": items}, open(out, "w"), indent=2)
    print(f"wrote {len(items)} items to {out} (of {len(tps)} true-positive pairs available)")


def judge(sheet, model):
    data = json.load(open(sheet))
    for it in data["items"]:
        user = (f"Requirement: {it['requirement']}\nDefect category: {it['category']}\n"
                f"Evidence: {it['evidence']}\nSuggested fix: {it['suggested_fix']}")
        resp = ollama.chat(model=model, think=False, format=Grade.model_json_schema(),
                           messages=[{"role": "system", "content": RUBRIC}, {"role": "user", "content": user}],
                           options={"temperature": 0, "seed": 0})
        it["judge_grade"] = Grade.model_validate_json(resp.message.content).grade
    data["judge_model"] = model
    json.dump(data, open(sheet, "w"), indent=2)
    print("judge grades:", dict(Counter(i["judge_grade"] for i in data["items"])))


def cohen_kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / n ** 2
    return None if pe == 1 else (po - pe) / (1 - pe)


def agree(sheet):
    items = [i for i in json.load(open(sheet))["items"] if i["human_grade"] is not None and i["judge_grade"] is not None]
    if not items:
        raise SystemExit("no items with both human_grade and judge_grade filled in")
    h, j = [i["human_grade"] for i in items], [i["judge_grade"] for i in items]
    exact = sum(x == y for x, y in zip(h, j)) / len(h)
    within1 = sum(abs(x - y) <= 1 for x, y in zip(h, j)) / len(h)
    k = cohen_kappa(h, j)
    print(f"n={len(h)}  exact agreement {exact:.2f}  within one {within1:.2f}  Cohen's kappa {k if k is None else round(k, 2)}")
    print("human dist:", dict(sorted(Counter(h).items())), "| judge dist:", dict(sorted(Counter(j).items())))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet"); s.add_argument("--labels", required=True); s.add_argument("--run", required=True)
    s.add_argument("--n", type=int, default=20); s.add_argument("--out", required=True); s.add_argument("--seed", type=int, default=0)
    j = sub.add_parser("judge"); j.add_argument("--sheet", required=True); j.add_argument("--model", required=True)
    a = sub.add_parser("agree"); a.add_argument("--sheet", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "sheet":
        make_sheet(args.labels, args.run, args.n, args.out, args.seed)
    elif args.cmd == "judge":
        judge(args.sheet, args.model)
    else:
        agree(args.sheet)


if __name__ == "__main__":
    main()
