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

## v2 and later (prompt v2 = labeling-rule definitions, no worked examples; analysis then findings; think off; T=0, seed 0; k = related requirements retrieved)

Dev set = data/labeled/starter_v1.json (labels by Joe). Test set = data/labeled/test_synthetic_v1.json (written and labeled by Claude, sealed until the config was frozen, then run once per model).

| Run | Model | Set | P / R / F1 | Note |
|---|---|---|---|---|
| v2 k=3, 3 repeats | qwen3:8b | dev | 0.464 / 0.684 / 0.553 (sd 0.000) | UNT F1 1.00, AMB 0.53, GAP 0.36 |
| v2 k=10, 1 run | qwen3:8b | dev | 0.417 / 0.526 / 0.465 | |
| v2 k=29 (whole set), 3 repeats | qwen3:8b | dev | 0.423 / 0.474 / 0.447 (sd 0.017) | more context scored worse; GAP recall 0 |
| v2 k=3, 3 repeats | gemma4:e4b | dev | 0.611 / 0.579 / 0.595 (sd 0.000) | |
| v2 k=3, 3 repeats | granite4.2:8b | dev | 0.402 / 0.491 / 0.442 (sd 0.040) | ~4x slower |
| v2 k=3 via n8n | qwen3:8b | dev | 0.464 / 0.684 / 0.553 | identical 28 pairs to the Python path |
| v2 k=3, 1 run | gemma4:e4b | test | 0.667 / 0.941 / 0.780 | |
| v2 k=3, 1 run | granite4.2:8b | test | 0.481 / 0.765 / 0.591 | |
| v2 k=3, 1 run | qwen3:8b | test | 0.310 / 0.529 / 0.391 | AMB 16 FP; GAP 0 TP |

Flag-everything baseline F1: 0.349 on dev, 0.318 on test.
Seconds per requirement (mean over 3 dev runs, includes model load amortized): gemma4:e4b 0.71, qwen3:8b 1.31, granite4.2:8b 5.14. All at 100% GPU.

## Things to remember when reading these numbers
- Prompt versions v0 to v2 were developed against qwen3:8b on the dev set. qwen3:8b dropped from 0.553 (dev) to 0.391 (test); the models not tuned against did not drop (gemma up, granite up). That pattern is what overfitting to the dev set looks like, but with 17 gold pairs on test it is one sample, not proof.
- The model ranking on dev (gemma > qwen > granite) and on test (gemma > granite > qwen) agree only on the winner.
- Repeat runs at T=0, seed=0 were identical for qwen3 and gemma4, and varied for granite. The earlier non-determinism (v0, verdict-first schema) was on borderline inputs.
- Test labels are Claude's, not Joe's, and the requirements are synthetic. Differences between dev and test can partly come from the labeler, not only the agent.
- Third-party sources said gemma4:e4b was 9.6 GB; ollama list shows 6.6 GB.

## System 1: Kev-9B (kev:9b-q4_K_M via Ollama /v1/systemone)

The requested `kev:9b-nvfp4` tag is an MLX build (Apple Silicon runner) and NVFP4 has no hardware path on an RTX 3080 (Ampere), so the same model's q4_K_M GGUF was used. A local variant `kev-9b-8k` (agent/modelfiles/) caps context at Kev's validated 8,192 tokens; Ollama otherwise loaded it at 73,728 tokens and put 18% on CPU. Probabilities were identical with the cap.

How it differs: one yes/no question per category per requirement, answered with a calibrated probability in one forward pass. No evidence quote, no suggested fix, no temperature or seed. Categories are answered independently, so the labeling rules' precedence can't be applied.

| Run | Set | Threshold | P / R / F1 | Ranking (average precision) | Brier | s / req |
|---|---|---|---|---|---|---|
| s1-kev9b-k3 r1-r3 | dev | 0.45 (chosen on dev r1) | 0.400 / 0.842 / 0.542, 0.542, 0.561 | 0.555 | 0.175 | 0.15 |
| test-s1-kev9b-k3-r1 | test | 0.45 (frozen) | 0.327 / 0.941 / 0.485 | 0.787 | 0.191 | 0.15 |

- Not deterministic: probabilities moved by up to 0.05 between identical repeats, enough to flip a flag near the threshold (one dev run scored 0.561 instead of 0.542).
- The F1 curve has a cliff: 0.542 at 0.45, 0.435 at 0.50. Many GAP probabilities sit between 0.44 and 0.51, so a small threshold change flips many flags. A threshold picked on 19 gold pairs is fragile.
- Overconfident against these labels: pairs it rated 0.4-0.6 were real 26% of the time on dev and 5% on test.
- GAP is the weak category (test: 20 false positives). AMB ranking is strong (test average precision 0.95).
- About 5x faster than gemma4:e4b (0.15 s vs 0.71 s per requirement).
