# Run log

Each row is one scored run. Newest last. Labels are frozen at data/labeled/starter_v1.json.

| Run | Prompt | Model | Overall P / R / F1 | AMB F1 | UNT F1 | GAP F1 | Note |
|---|---|---|---|---|---|---|---|
| v0-qwen3-8b-r1 | v0 naive, verdict-first schema | qwen3:8b, think off, T=0 | n/a / 0.000 / 0.000 | 0.000 | 0.000 | 0.000 | 1 flag in 30 requirements (TP 0, FP 1, FN 19). 8.1 s total on GPU. |
| v1-qwen3-8b-r1 | v1: analysis then findings, no verdict | qwen3:8b, think off, T=0 | 0.258 / 0.421 / 0.320 | 0.400 | 0.182 | 0.286 | TP 8, FP 23, FN 11. 25 of 30 requirements flagged; 10 of 11 clean ones flagged. 58 s. Below the flag-everything baseline (F1 0.349). |

## Predictions made before the v0 run (Joe)
- Precision would be worse than recall. **Wrong**: precision was undefined-to-zero because the agent flagged almost nothing; recall was the failure.
- Bias toward "clean" would continue. **Right.**
- Worst category: AMB. **Not distinguishable**: all three categories scored 0.

## What went wrong (README "What I got wrong" material)
1. **Verdict-first schema made the model say "clean".** The model had to commit to `clean`/`defective` as its first token, before writing any reasoning. For obviously vague text ("returned quickly", "user-friendly") it said clean 29 of 30 times. We chose this design on the argument that it gives the model a legitimate way to say "no issues"; in practice it gave the model an easy way to skip the work.
   - Diagnosis: the same vague requirement was flagged when sent as bare text or with a different ID label, and not flagged with the `REQ-004:` prefix, so the output was sensitive to trivial prompt changes. Removing the verdict field (findings-only schema) made REQ-004/005/010 flag consistently across 3 seeds. Not yet scored.
   - Side effect seen in the same diagnostic: without the gate, clearly specified requirements (REQ-001, REQ-009) also got flagged. That is the precision cost; expect the next run to swap the recall problem for a precision problem.
2. **temperature 0 + fixed seed was not deterministic** on Ollama: the same prompt returned clean, then defective. Repeat runs are required before any two scores are compared (step 5).
3. Diagnostic calls looked only at requirement text, not labels. They are not scored.

## v1 (Joe predicted: precision would be the weaker number)
- **Right.** P 0.258 vs R 0.421. No F1 prediction was made.
- Of 23 false positives, 12 were on clean requirements and 11 were the right requirement with the wrong category (AMB/UNT/GAP mixed up in every direction).
- The agent flagged 25 of 30 requirements. A model told to "report problems" reports problems; removing the verdict gate moved the failure from "never flags" to "always flags".
- F1 0.320 is *below* a flag-everything agent (0.349 on this set). Recall improved from 0.0 to 0.42 but the agent is not yet better than a lazy baseline on F1.
- The v1 code was already committed (aaaa8b6) before I applied it a second time; a duplicate class resulted and was removed. I had wrongly told Joe nothing was applied without checking git log.
