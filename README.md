# reqcheck-eval

**Status: in progress.** The agent, scorer, model comparison, n8n workflow and judge calibration are done. The labeler self-consistency check is not done yet (see "How quality is scored").

Self-hosted requirements-review agent (Ollama + Qdrant + n8n) that flags gaps, ambiguity, and untestable statements, with an eval harness that scores its output against hand-labeled ground truth.

## Results

Best configuration so far: **gemma4:e4b (Q4_K_M), prompt v2, 3 related requirements as context, temperature 0.**

| Metric | Dev set (30 reqs, labeled by me) | Test set (30 reqs, synthetic, labeled by Claude) |
|---|---|---|
| Gold issue pairs | 19 | 17 |
| Precision (flagged issues that were real) | 0.611 | 0.667 |
| Recall (real issues the agent caught) | 0.579 | 0.941 |
| F1 | 0.595 (3 identical runs) | 0.780 (1 run) |
| Flag-everything baseline F1 | 0.349 | 0.318 |
| Avg. time per requirement | 0.71 s | 1.05 s |
| Hardware | Ryzen 7 7800X3D, 32 GB RAM, RTX 3080 10 GB, 100% GPU | same |

All three models, same prompt, same settings:

| Model (Q4_K_M) | Dev F1 (mean of 3 runs) | Test F1 (1 run) | s / requirement (dev) |
|---|---|---|---|
| gemma4:e4b | 0.595 | 0.780 | 0.71 |
| granite4.2:8b | 0.442 (sd 0.04) | 0.591 | 5.14 |
| qwen3:8b | 0.553 | 0.391 | 1.31 |

Takeaway: gemma4:e4b was best on both sets and fastest, but with 19 and 17 gold pairs a single pair moves a score by 2 to 5 points, so only the large gaps (gemma vs. granite on dev, qwen's drop from dev to test) should be believed. The prompt was developed against qwen3:8b on the dev set, and qwen3:8b is the model that lost the most on the held-out test set.

Full run history, including failed attempts: [results/LOG.md](results/LOG.md).

## What it does

Takes a requirements document, retrieves related context from a vector store, and flags:

1. **Gaps** (`GAP`): missing information needed to design tests (an undefined term, a missing trigger, actor, or failure behavior)
2. **Ambiguity** (`AMB`): a measurable property with a missing value ("promptly", "several")
3. **Untestable statements** (`UNT`): subjective or unbounded wording with no observable pass/fail criterion

Each flag includes the requirement ID, category, quoted evidence, and a suggested fix.

## Architecture

```
POST {req_id, text} -> n8n webhook
                          |
                          +-> Ollama embed (nomic-embed-text) -> Qdrant top-k similar requirements
                          |
                          +-> build prompt (rules + related requirements) -> Ollama chat
                                                                              |
                                                          JSON-schema-constrained findings
                                                                              |
                                                               findings.json -> eval/score.py
```

The same pipeline exists as plain Python (`agent/run.py`) and as an n8n workflow (`workflows/reqcheck.json`, generated from the Python prompt and schema by `workflows/build_workflow.py` so they cannot drift). On the dev set both produce identical findings.

**Stack:** Ollama (model runtime), Qdrant (vector DB), n8n (orchestration), Python (agent and eval harness).

**Design choices that came from measurements, not assumptions**
- The LLM checks every requirement; retrieval only supplies cross-reference context. Retrieval alone finds topical neighbors, not defects.
- Retrieval depth matters: k=3 beat k=29 (the whole set) for qwen3:8b, F1 0.553 vs 0.447. More context was not better.
- The agent code reads only `req_id` and `text`; it cannot see the labels.

## How quality is scored

### Ground truth
- **Dev set:** 30 requirements for a customer-order portal (synthetic), labeled by me by hand before any agent run. Labels are `AMB`, `UNT`, `GAP`; one requirement can carry several.
- **Test set:** 30 requirements for a clinic scheduler, written and labeled by Claude, labeled by construction (each defect planted) under my labeling rules. Sealed until the configuration was frozen, then run once per model. These are not my labels; I made an exception to my own rule because I was short on time.
- Labeling rules, precedence between categories, and worked examples: [eval/labeling-rules.md](eval/labeling-rules.md)

### Metrics
- **Precision / recall / F1** per category and overall; overall is micro-averaged.
- The unit is the `(req_id, category)` pair. A flag is correct only if both match. Right requirement with the wrong category counts as one false positive and one false negative.
- F1 is 0 (not n/a) when there are pairs but no true positives. Full rules: [eval/matching.md](eval/matching.md)
- A naive baseline is reported next to every score: an agent that flags everything gets F1 0.349 on dev.

### LLM-as-judge (suggested-fix quality only)
- Tooling is built ([eval/judge.py](eval/judge.py)): 20 true-positive fixes sampled into [data/calibration/fix_sheet.json](data/calibration/fix_sheet.json), graded 1 to 3. The judge (qwen3:8b, a different model from the one that wrote the fixes) writes its grades to a separate file so the human grades blind.
- **Calibration (20 fixes, my grades vs. the judge's):** exact agreement 0.65, within one grade 0.95, Cohen's kappa **0.15**. The judge gave a 3 to 19 of 20 fixes; I gave 3 to 12, a 2 to 7 and a 1 to 1. The raw agreement mostly reflects the judge answering 3 almost every time, which kappa corrects for. **The judge failed calibration, so no judge score is reported as a quality number.**
- To retry, I would tighten the rubric or change the judge and re-check on a fresh sample of fixes, not on these 20 (tuning on them would just fit my grades).

### Run-to-run variance
- At temperature 0 with a fixed seed, three repeats were identical for gemma4:e4b and qwen3:8b (sd 0.000) and varied for granite4.2:8b (F1 sd 0.040).
- Identical repeats do not mean the numbers are precise: the sampling error from only 17 to 19 gold pairs is much larger than the run-to-run spread.

### Labeler consistency
- Re-labeling a random 10 requirements after 48 hours to measure self-agreement: TODO (not done).

## What I got wrong

- **The first baseline scored F1 0.000.** My schema made the model write `clean` or `defective` before any reasoning, and for obviously vague requirements it said "clean" 29 of 30 times. I had chosen that design to give the model a legitimate way to say "no issues". Fix: write an analysis first, drop the verdict field. That swung the failure the other way (25 of 30 requirements flagged, F1 0.320, below the flag-everything baseline of 0.349).
- **Putting the labeling rules into the prompt did the most good** (F1 0.320 to 0.553 on qwen3:8b). I deliberately left out the rules file's worked examples because they are nearly the same wording as dev items, which would leak answers.
- **More retrieved context made it worse**, which I did not expect (k=29: F1 0.447 vs k=3: 0.553; GAP recall fell to 0). I have not isolated the cause.
- **I tuned on one model and one dataset.** qwen3:8b fell from 0.553 on dev to 0.391 on the sealed test set while the other two models rose. The prompt is probably fitted to qwen3 and the dev wording.
- **Temperature 0 and a fixed seed did not guarantee identical output** on borderline inputs in the verdict-first version (same prompt, same seed, different verdict).
- **Ollama silently ran on CPU** after a kernel update left the NVIDIA module missing for the new kernel, and a stale GPU scan kept it on CPU even after the driver was fixed. Only `ollama ps` showed it. Every run now records the GPU fraction.
- **Process slips:** I took a third-party model size (gemma4:e4b at 9.6 GB) as fact; it is 6.6 GB. I also applied the v1 change twice, because I did not check `git log` first.
- TODO: where my own labels turned out to be inconsistent (needs the self-consistency check).

## Quickstart

```bash
# 1. Run the models
ollama pull nomic-embed-text gemma4:e4b qwen3:8b granite4.2:8b

# 2. Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# 3. Python environment
python -m venv .venv && .venv/bin/pip install ollama qdrant-client pydantic

# 4. Run the agent on the dev set and score it
.venv/bin/python -m agent.run --data data/labeled/starter_v1.json --model gemma4:e4b --prompt v2 --out results/my-run
.venv/bin/python -m eval.score --labels data/labeled/starter_v1.json --findings results/my-run/findings.json

# 5. Optional: the same pipeline in n8n (host network so it can reach Ollama and Qdrant on localhost)
docker run -d --name n8n --network host -v n8n_data:/home/node/.n8n -v "$PWD/workflows:/workflows:ro" docker.n8n.io/n8nio/n8n
docker exec n8n n8n import:workflow --input=/workflows/reqcheck.json
docker exec n8n n8n publish:workflow --id=<id from: docker exec n8n n8n list:workflow> && docker restart n8n
.venv/bin/python workflows/run_via_n8n.py --data data/labeled/starter_v1.json --out results/my-n8n-run

# 6. Tests and repeat-run summary
.venv/bin/python -m unittest discover -s eval/tests -t .
.venv/bin/python -m eval.summarize --labels data/labeled/starter_v1.json results/runA-r1 results/runA-r2
```

The n8n workflow is generated for qwen3:8b by default; regenerate with `python workflows/build_workflow.py --model gemma4:e4b > workflows/reqcheck.json` to match the best configuration.

## Repo layout

```
reqcheck-eval/
  data/
    labeled/          # ground truth: starter_v1.json (dev, my labels), test_synthetic_v1.json (sealed test)
    calibration/      # fix-quality grading sheet for the judge calibration
  workflows/          # n8n workflow JSON, its generator, and a driver script
  agent/              # prompts, schema, retrieval, runner
  eval/               # scorer, matching rules, labeling rules, judge, tests
  results/            # one folder per run, plus LOG.md
  README.md
```

## Limitations

- Small labeled sets (30 requirements each, 17 to 19 gold pairs): results are directional, not statistically strong.
- Single labeler per set and no inter-annotator agreement. The test set is labeled by Claude, not me.
- Both sets are synthetic and tidier than real documents; real client documents will differ.
- Three models of similar size (7.5B to 8.8B, all Q4_K_M); no larger models and no hosted models tested.
- Prompts were tuned against the dev set on one model; the test set was run once per model after freezing, but it is small.
- Set-level gaps (whole requirements missing) are out of scope.

## Next steps

- Retry the fix-quality judge with a stricter rubric or different model, calibrated on a fresh sample
- Re-label 10 requirements for the self-consistency check
- Try `think=True` as a separate experiment and test the context-distraction hypothesis for the k=29 drop
- Check the test set against real requirement text (for example sentences sampled from the public PURE dataset)
- Add a test-design agent that turns accepted requirements into test cases
- Write findings to Jira via API

## License

TODO
