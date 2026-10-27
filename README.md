# reqcheck-eval

**Status: in progress.** Everything below works except one check: re-labeling a sample of my own labels to measure how consistent I was.

A self-hosted agent that reviews software requirements and flags three kinds of defects: ambiguity, untestable wording, and missing information. It runs entirely on one workstation (Ollama, Qdrant, n8n). The main point of the project is the evaluation harness that scores the agent against labels I wrote by hand, so every claim about quality is backed by a number.

For a plain-English walkthrough aimed at non-engineers and architects, see [docs/overview.md](docs/overview.md).

## Results

The best setup is **gemma4:e4b** with prompt v2, 3 related requirements as context, and temperature 0.

| | Dev set (labeled by me) | Test set (labeled by Claude) |
|---|---|---|
| Requirements / real defects | 30 / 19 | 30 / 17 |
| Precision (share of flags that were real) | 0.611 | 0.667 |
| Recall (share of real defects caught) | 0.579 | 0.941 |
| F1 | 0.595 (3 identical runs) | 0.780 (1 run) |
| F1 of an agent that flags everything | 0.349 | 0.318 |
| Time per requirement | 0.71 s | 1.05 s |

All three models, same prompt and settings, on a Ryzen 7 7800X3D with an RTX 3080 (10 GB), fully on the GPU:

| Model (all Q4_K_M) | Dev F1 (average of 3 runs) | Test F1 (1 run) | Time per requirement |
|---|---|---|---|
| gemma4:e4b | 0.595 | 0.780 | 0.71 s |
| qwen3:8b | 0.553 | 0.391 | 1.31 s |
| granite4.2:8b | 0.442 (±0.04) | 0.591 | 5.14 s |

gemma4:e4b was best on both sets and also the fastest. With fewer than 20 real defects per set, one requirement can move a score by 2 to 5 points, so only the large differences mean much. The most telling one: I developed the prompt against qwen3:8b, and that model is the one that dropped sharply on the test set it had never seen.

Every run, including the failures, is logged in [results/LOG.md](results/LOG.md).

## What it flags

| Code | Defect | Example |
|---|---|---|
| `AMB` | Ambiguity: something measurable is named but its value is missing | "respond **promptly**" |
| `UNT` | Untestable: subjective or unlimited wording with no pass/fail test | "must be **seamless**", "**always** available" |
| `GAP` | Missing information a tester would need | "follow **the pharmacy workflow**" (defined nowhere) |

Each finding names the requirement and category, quotes the words that triggered it, and suggests a fix. The full definitions are in [eval/labeling-rules.md](eval/labeling-rules.md).

## How it works

```
requirement -> embed (nomic-embed-text) -> Qdrant: 3 most similar other requirements
            -> prompt = labeling rules + related requirements + this requirement
            -> Ollama, with output forced into a JSON schema: { analysis, findings[] }
            -> findings.json -> scorer
```

- **The model reviews every requirement.** Retrieval only adds context, such as whether a term is defined elsewhere. Searching the vector database for "vague requirements" found topical neighbors, not defects.
- **The model writes its analysis before its findings**, and an empty list means the requirement is clean.
- **The agent never sees the labels.** It reads only the ID and text of each requirement.
- **The pipeline also runs as an n8n workflow.** The workflow is generated from the Python prompt and schema, so the two can't drift. On the dev set both versions produced identical findings.

## How quality is scored

**Ground truth.**
- **Dev set:** I labeled 30 requirements by hand before the agent ever ran.
- **Test set:** a separate set of 30, which Claude wrote and labeled by planting each defect deliberately. It stayed sealed until the setup was final, and then each model ran on it once. That makes it the one honest check on whether the prompt tuning carries over to new text.

**Scoring.**
- A finding counts only if both the requirement and the category match a label. Flagging the right requirement with the wrong category counts as one false alarm plus one miss.
- I report precision, recall and F1 overall and per category, always next to the flag-everything baseline.
- The detailed rules are in [eval/matching.md](eval/matching.md), and the scorer has unit tests.

**Repeatability.** At temperature 0 with a fixed seed:
- Three repeat runs were identical for gemma4 and qwen3, and varied slightly for granite.
- The small number of labeled defects is a much bigger source of uncertainty than run-to-run noise.

**AI judge for fix quality.**
- Suggested fixes have no single right answer, so I tried having a second model (qwen3:8b) grade them from 1 to 3.
- I then graded the same 20 fixes myself without seeing its grades.
- We agreed 65% of the time, but only because the judge gave nearly everything (19 of 20) the top grade.
- Corrected for chance agreement, Cohen's kappa was **0.15**, which is barely better than chance. The judge failed, so I don't report any judge scores.

## What I got wrong

- **The first version scored F1 0.0.** I asked the model to say "clean" or "defective" before giving any reasoning, and it said "clean" for 29 of 30 requirements. Letting it write an analysis first fixed that, but it then flagged 25 of 30 and scored 0.320, which is worse than flagging everything.
- **Adding my written labeling rules to the prompt made the biggest difference** (0.320 to 0.553). I left out the rules file's examples, because they are worded almost the same as dev-set items and would have leaked answers.
- **More context made it worse.** Showing the model all the other requirements instead of the 3 most similar ones dropped F1 from 0.553 to 0.447, and it stopped finding gaps entirely. I haven't pinned down why.
- **I tuned on one model and one dataset**, and the test set exposed it: qwen3:8b fell from 0.553 to 0.391 while the other two models improved.
- **Temperature 0 and a fixed seed didn't guarantee the same answer** on borderline cases in the first version.
- **Ollama silently fell back to the CPU** after a kernel update left the NVIDIA driver module missing. Only `ollama ps` showed it. Every run now records how much of it ran on the GPU.

## Quickstart

```bash
# Models
for m in nomic-embed-text gemma4:e4b qwen3:8b granite4.2:8b; do ollama pull $m; done

# Qdrant and Python
docker run -d -p 6333:6333 qdrant/qdrant
python -m venv .venv && .venv/bin/pip install ollama qdrant-client pydantic

# Run the agent on the dev set and score it
.venv/bin/python -m agent.run --data data/labeled/starter_v1.json --model gemma4:e4b --prompt v2 --out results/my-run
.venv/bin/python -m eval.score --labels data/labeled/starter_v1.json --findings results/my-run/findings.json

# Tests, and a summary across repeat runs
.venv/bin/python -m unittest discover -s eval/tests -t .
.venv/bin/python -m eval.summarize --labels data/labeled/starter_v1.json results/run-r1 results/run-r2
```

To run the same pipeline through n8n:

```bash
.venv/bin/python workflows/build_workflow.py --model gemma4:e4b > workflows/reqcheck.json
docker run -d --name n8n --network host -v n8n_data:/home/node/.n8n -v "$PWD/workflows:/workflows:ro" docker.n8n.io/n8nio/n8n
docker exec n8n n8n import:workflow --input=/workflows/reqcheck.json
docker exec n8n n8n list:workflow            # note the workflow ID
docker exec n8n n8n publish:workflow --id=<ID> && docker restart n8n
.venv/bin/python workflows/run_via_n8n.py --data data/labeled/starter_v1.json --out results/my-n8n-run
```

n8n uses host networking so it can reach Ollama and Qdrant on localhost. It retrieves context from whichever requirements file `agent.run` indexed last.

## Repo layout

```
agent/        prompts, output schema, retrieval, runner
eval/         scorer, labeling and matching rules, AI judge, tests
data/labeled/ dev set (my labels) and sealed test set
data/calibration/  fixes graded by me and by the AI judge
workflows/    n8n workflow, its generator, and a driver script
results/      one folder per run, plus LOG.md
docs/         plain-English project overview
```

## Limitations

- Small sets (30 requirements each, under 20 real defects), so the results are directional rather than statistically strong.
- Each set has a single labeler, and the test set was labeled by Claude rather than by me.
- Both sets are synthetic and tidier than real project documents.
- Only three models, all around 8B parameters and 4-bit quantized.
- All runs share one Qdrant collection, rebuilt from whichever file was processed last. A real deployment needs one per document.
- The agent checks individual requirements, so it can't notice that a whole requirement is missing.

## Next steps

- Re-label 10 requirements to measure my own consistency
- Retry the fix-quality judge with a stricter rubric, checked against a fresh sample
- Test the model's built-in reasoning mode, and find out why more context hurt
- Run against real requirement text, such as the public PURE dataset
- Turn accepted requirements into test cases, and write findings to Jira

## License

TODO
