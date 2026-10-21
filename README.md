# reqcheck-eval

Self-hosted requirements-review agent (Ollama + Qdrant + n8n) that flags gaps, ambiguity, and untestable statements, with an eval harness that scores its output against hand-labeled ground truth.

## Results

<!-- Fill this in FIRST. This is the first screen a reader sees. Numbers beat diagrams. -->

| Metric | Value |
|---|---|
| Requirements hand-labeled | TODO (target: 25-30) |
| Issue categories | Gap / Ambiguity / Untestable |
| Precision (flagged issues that were real) | TODO |
| Recall (real issues the agent caught) | TODO |
| F1 | TODO |
| Model / quantization | TODO (e.g. Llama 3.x 8B Q4 via Ollama) |
| Avg. time per requirement | TODO |
| Hardware | TODO |

One-sentence takeaway: TODO (e.g. "Strong on ambiguity, weak on missing-requirement gaps; recall dropped when ...").

## What it does

Takes a requirements document, retrieves related context from a vector store, and flags:

1. **Gaps**: missing information needed to design tests (inputs, error states, limits, actors)
2. **Ambiguity**: vague terms ("fast", "user-friendly", "as appropriate")
3. **Untestable statements**: requirements with no observable pass/fail criterion

Each flag includes the requirement ID, category, quoted evidence, and a suggested fix.

## Architecture

```
Requirements doc -> n8n workflow -> chunk + embed -> Qdrant
                         |                              |
                         +--> prompt + retrieved context --> Ollama (local LLM)
                                                            |
                                                  structured JSON findings
                                                            |
                                                      eval harness
```

TODO: replace with a real diagram once the pipeline works.

**Stack:** Ollama (model runtime), Qdrant (vector DB), n8n (orchestration), Python (eval harness).

## How quality is scored

### Ground truth
- TODO: number of requirements, source (synthetic, public sample SRS docs, redacted real ones)
- Labeled by hand by me, one label per issue: requirement ID + category
- Labeling rules: TODO (write down the rules you used so the labels are reproducible; ambiguous cases and how you resolved them)

### Metrics
- **Precision / recall / F1** per category and overall
- A flag counts as correct if: TODO (same requirement ID and same category? Partial credit for right requirement, wrong category?)
- Matching rules documented in `eval/matching.md`

### LLM-as-judge (optional)
- Used for: TODO (e.g. scoring quality of suggested fixes, which has no exact-match ground truth)
- **Calibration:** judge scores compared against my own scores on N items; agreement = TODO. If agreement is low, the judge score is not reported as a quality number.

### Run-to-run variance
- Ran each eval N times at temperature TODO; spread = TODO

## What I got wrong

<!-- Keep this section honest. It is the most useful part of the README. -->

- TODO: failure mode 1 (e.g. "flagged every use of 'should' as ambiguous; precision dropped")
- TODO: failure mode 2
- TODO: a prompt or retrieval change that made things worse, and what the eval showed
- TODO: where my own labels turned out to be inconsistent

## Quickstart

```bash
# 1. Run the model
ollama pull TODO_MODEL

# 2. Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# 3. Start n8n and import the workflow
TODO: command + path to workflow JSON

# 4. Run the eval
python -m eval.run --data data/labeled --out results/
```

## Repo layout

```
reqcheck-eval/
  data/
    requirements/     # source documents
    labeled/          # ground-truth labels (JSON)
  workflows/          # exported n8n workflow(s)
  agent/              # prompts, schema, retrieval code
  eval/               # scoring, matching rules, judge calibration
  results/            # run outputs, one folder per run
  README.md
```

## Limitations

- Small labeled set: results are directional, not statistically strong
- One model family tested: TODO
- Requirements are TODO (synthetic / public / redacted); real client documents will differ
- Single labeler, so no inter-annotator agreement

## Next steps

- TODO: add test-design agent that turns accepted requirements into test cases
- TODO: compare two or more models on the same eval
- TODO: write findings to Jira via API

## License

TODO
