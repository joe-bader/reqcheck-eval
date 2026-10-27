# reqcheck-eval: technical overview

A self-hosted agent that reviews software requirements and flags ambiguity, untestable wording and missing information, plus the evaluation harness that scores it against labels I wrote by hand. Runs on one workstation with Ollama, Qdrant and n8n. The harness is the point: every quality claim here is a measured number.

Plain-language summary: [README](../README.md). Terms: [glossary](glossary.md). Setup and commands: [running.md](running.md).

## Results

Best accuracy: **qwen3.6:35b-a3b**. Best accuracy for the speed: **gemma4:e4b**. Both use prompt v2, 3 related requirements as context, temperature 0. The table below is gemma4:e4b.

| | Dev set (my labels) | Sealed test set (Claude's labels) |
|---|---|---|
| Requirements / real defects | 30 / 19 | 30 / 17 |
| Precision | 0.611 | 0.667 |
| Recall | 0.579 | 0.941 |
| F1 | 0.595 (3 identical runs) | 0.780 (1 run) |
| F1 of an agent that flags everything | 0.349 | 0.318 |
| Time per requirement (RTX 3080) | 0.71 s | 1.05 s |

| Model (all Q4_K_M) | Size | Dev F1 | Test F1 | s / req |
|---|---|---|---|---|
| qwen3.6:35b-a3b | 35B (3B active) | **0.769** | 0.732 | 5.91 |
| gemma4:e4b | 7.5B | 0.595 | **0.780** | 0.71 |
| qwen3:8b | 8.2B | 0.553 | 0.391 | 1.31 |
| granite4.2:8b | 8.8B | 0.442 ±0.04 | 0.591 | 5.14 |
| Kev-9B (System 1) | 9B | 0.542 | 0.485 | **0.15** |

With under 20 real defects per set, one requirement moves a score by 2 to 5 points, so only large gaps mean much:
- **qwen3.6 vs. gemma4:** qwen3.6 is clearly ahead on dev, and the two are tied on test. qwen3.6 is about 4× larger, doesn't fit in 10 GB of VRAM (its experts run from system RAM), and is 8× slower.
- **qwen3:8b on unseen text:** I tuned the prompt against qwen3:8b, and it is the model that fell on the test set. qwen3.6 is from the same family, which may have helped it on dev.

Full run history in [results/LOG.md](../results/LOG.md).

**Kev-9B is a different kind of model.** It is a "System 1" decision model: no generated text, no quoted evidence and no fixes, just a calibrated probability for each defect type in one forward pass. Flags come from a probability threshold (0.45, chosen on dev and frozen for test). It's 5× faster than gemma4 but over-flags gaps, and its probabilities were overconfident against my labels. The requested NVFP4 build runs only on Apple Silicon, so I used the same model's Q4_K_M build.

## What it flags

| Code | Defect | Example |
|---|---|---|
| `AMB` | Something measurable is named, but no value | "respond **promptly**" |
| `UNT` | Subjective or unlimited wording, no pass/fail test | "must be **seamless**", "**always** available" |
| `GAP` | Information a tester needs is absent | "follow **the pharmacy workflow**" |

Definitions and tie-break rules: [eval/labeling-rules.md](../eval/labeling-rules.md).

## How it works

```
requirement -> embed (nomic-embed-text) -> Qdrant: 3 most similar other requirements
            -> prompt = labeling rules + neighbors + this requirement
            -> Ollama, output forced into a JSON schema { analysis, findings[] }
            -> findings.json -> eval/score.py
```

- The model reviews every requirement. Retrieval only supplies context; searching the vector DB for "vague requirements" found topical neighbors, not defects.
- The model writes its analysis before its findings. An empty list means clean.
- The agent reads only requirement ID and text, never the labels.
- The same pipeline runs as an n8n workflow generated from the Python prompt and schema (`workflows/`). Both paths produced identical findings.

## How quality is scored

- **Dev set:** 30 requirements I labeled before the agent ever ran. **Test set:** 30 more, written and labeled by Claude, sealed until the setup was final, then run once per model.
- A finding counts only if requirement *and* category match. Wrong category is one false alarm plus one miss. Rules: [eval/matching.md](../eval/matching.md).
- Precision, recall and F1 are reported overall and per category, next to the flag-everything baseline.
- **Repeatability:** 3 runs at temperature 0 were identical for gemma4 and qwen3; granite varied slightly.
- **My consistency:** re-labeling 10 requirements blind five days later matched 29 of 30 decisions (Cohen's kappa 0.89). The one reversal was REQ-003, whether "inactivity" counts as an undefined term.
- **AI judge for fix quality:** a second model graded 20 fixes 1 to 3; I graded them blind. It gave 19 of 20 the top grade; kappa 0.15. Failed calibration, so no judge scores are reported.

## What I got wrong

- **First version: F1 0.0.** Asking for a clean/defective verdict before any reasoning made the model say "clean" for 29 of 30. Reasoning first fixed it, then it flagged 25 of 30 (F1 0.320, below flag-everything).
- **Adding the labeling rules to the prompt was the biggest gain** (0.320 to 0.553). I left out the rules' examples, which are worded like dev items and would leak answers.
- **More context hurt.** All other requirements instead of 3 neighbors: 0.553 to 0.447, and gap recall fell to zero. Cause not isolated.
- **Overfit to one model and one set.** qwen3:8b fell from 0.553 to 0.391 on the test set while the others rose.
- **A run crashed on one bad answer.** qwen3.6 sometimes writes its analysis without ever closing it, until it hits the output limit, and the half-finished JSON crashed the whole run. It now caps output length and counts the bad answer as no findings (3 of 30 on dev, the same 3 every run).
- **Ollama silently fell back to CPU** after a kernel update broke the NVIDIA module. Every run now records its GPU fraction.

## Limitations

Small synthetic sets (under 20 real defects each). One labeler per set; the test set is Claude's, not mine. Five models, all 4-bit; only one larger than ~9B. One shared Qdrant collection, rebuilt per run. Can't detect a missing requirement, only defects in existing ones.
