# reqcheck-eval: project overview

**Status: proof of concept, in progress.** Every number in this document comes from a run recorded in [results/LOG.md](../results/LOG.md).

## 1. The short version

Software teams write *requirements*: statements such as "the system shall send a confirmation email within 60 seconds." Weak requirements are expensive. A vague one ("search should be fast") lets two people build and test two different things, and the problem usually surfaces late, in testing or after release.

This project is a **requirements reviewer that runs on a single local workstation**. It reads each requirement and flags three kinds of defects, quoting the offending words and suggesting a fix. No data leaves the machine.

The more important part is the **evaluation harness**. Anyone can wire up an AI model and get plausible-sounding output. The hard part is knowing whether the output is *correct* and whether a change made it better or worse. This project answers that with a hand-labeled answer key, a scoring program, and a log of every experiment, including the ones that failed.

**Where it stands:** the best configuration finds roughly 6 in 10 of the real defects on the main test set and about 6 in 10 of what it flags is real. That is useful as a first-pass assistant for a human reviewer. It is not reliable enough to run unattended. The sections below say what is and isn't proven.

## 2. What it checks

| Code | Name | Plain meaning | Example (not from the data) |
|---|---|---|---|
| AMB | Ambiguity | Something measurable is named, but the value is missing or vague | "respond promptly" (how many seconds?) |
| UNT | Untestable | Subjective or unlimited wording; no test could give a definite pass/fail | "must be delightful to use" |
| GAP | Gap | Information a tester would need is simply absent | "follow the pharmacy workflow" (defined nowhere) |

The exact definitions, the tie-break order when text fits several categories, and what does *not* count as a defect are written in [eval/labeling-rules.md](../eval/labeling-rules.md). Those rules are the project's specification, and they are also pasted into the AI's instructions.

## 3. How it works

```
                 requirement text
                        |
        +---------------+----------------+
        |                                |
  embed with nomic-embed-text      (the requirement itself)
        |                                |
  Qdrant vector database                 |
  returns the 3 most similar             |
  *other* requirements                   |
        |                                |
        +---------------+----------------+
                        |
         prompt = rules + related requirements + this requirement
                        |
        local language model (Ollama), output forced into a JSON shape
                        |
        { analysis, findings: [ {category, evidence, suggested_fix} ] }
                        |
                  findings.json  ->  scorer  ->  precision / recall / F1
```

Step by step:

1. **Each requirement is reviewed on its own**, one model call per requirement. The model is asked about *every* requirement because an earlier experiment showed that searching for "vague" requirements by meaning does not work (see section 7).
2. **Related requirements are retrieved as context.** Some defects only show up in comparison: "use the standard timeout" is a gap only if no other requirement defines it. Retrieval means finding nearby text by *meaning* rather than by keyword. Each requirement is converted to a list of numbers (an *embedding*) so that similar meanings are close together, and those lists are stored in a vector database (Qdrant).
3. **The model must answer in a fixed shape.** Ollama enforces a JSON schema while the model generates, much like a typed API contract. The model writes a short analysis first, then the findings. An empty findings list means "clean."
4. **A separate program scores the result.** It never calls an AI model, so the grading is deterministic and unit-tested (13 tests).

### Components

| Part | Location | Role |
|---|---|---|
| Prompts and schema | `agent/prompts.py`, `agent/schema.py` | Versioned instructions (v0 to v2) and the output contract |
| Retrieval | `agent/index.py` | Loads requirement text only (never the labels), embeds, indexes, fetches neighbors |
| Runner | `agent/run.py` | Loops over requirements, writes `findings.json` and a metadata file recording model, settings, GPU use and timing |
| Scorer | `eval/score.py` | Compares findings to the answer key; precision, recall, F1 overall and per category |
| Judge | `eval/judge.py` | Optional AI grader for fix quality, with a check against a human |
| n8n workflow | `workflows/` | The same pipeline as a visual, schedulable workflow (see section 8) |
| Run history | `results/` | One folder per run, plus a readable log |

## 4. How quality is measured

**The answer key.** I labeled 30 requirements by hand *before the agent ever ran*, using the written rules. This is the main ("dev") set: 19 real defects across 30 requirements, and 11 requirements are clean.

**What counts as correct.** The unit is a *(requirement, category)* pair. If the answer key says REQ-007 has an ambiguity and the agent flags REQ-007 as ambiguous, that is a hit. Flagging it as the wrong category does not count; it is scored as both a false alarm and a miss. Quoted evidence and the suggested fix are not compared by this scorer.

**The three numbers** (in terms of a smoke detector):

- **Precision:** of the alarms that sounded, how many were real fires? Low precision means false alarms and a team that stops listening.
- **Recall:** of the real fires, how many sounded an alarm? Low recall means defects slip through.
- **F1:** one number that is high only when both are decent. It punishes lopsidedness: 90% precision with 10% recall scores 0.18.

**A reference point.** An agent that flags *everything* gets perfect recall and poor precision, and scores F1 0.349 on the main set. Every result is read against that. A score of 0.32 sounds like partial progress until you see that a program that doesn't read the text scores 0.35.

**A sealed test set.** Tuning prompts against the same 30 requirements risks fitting the answer key rather than learning the task. So a second, separate set of 30 (a clinic appointment scheduler) was written and **kept unused until the configuration was frozen**, then run once per model. Its labels were created by Claude, not by me, by planting each defect on purpose. That is a stated exception, and it limits how far the numbers can be trusted (section 9).

## 5. Results

Same prompt, same settings (prompt v2, 3 retrieved neighbors, temperature 0), all on the GPU:

| Model | Main set F1 (avg of 3 runs) | Sealed test F1 (1 run) | Seconds per requirement |
|---|---|---|---|
| gemma4:e4b | **0.595** | **0.780** | 0.71 |
| qwen3:8b | 0.553 | 0.391 | 1.31 |
| granite4.2:8b | 0.442 | 0.591 | 5.14 |

Best configuration on the main set: precision 0.611, recall 0.579. On the sealed set: precision 0.667, recall 0.941.

**How to read this.**

- gemma4:e4b won on both sets and is also the fastest, so it is the clear pick.
- With 17 to 19 real defects per set, **one pair moves a score by 2 to 5 points.** Small gaps are noise. The believable results are the large ones: gemma versus granite on the main set, and qwen3's drop from 0.553 to 0.391 on the sealed set.
- The prompt was developed against qwen3 on the main set. That model is the one that fell furthest on unseen data, while the other two did not. This is what overfitting looks like, though one small sample cannot prove it.

## 6. Design decisions and why

| Decision | Alternatives | Why this one |
|---|---|---|
| Review every requirement with the model; use retrieval only for context | Search the database for "problem requirements" | Measured: similarity search finds topical neighbors, not defects (it missed two obviously vague requirements) |
| Output schema: analysis first, then findings, no clean/defective field | Verdict first; findings only; built-in model reasoning | Verdict-first made the model say "clean" before thinking (F1 0.000). Findings-only over-flagged. Analysis-first fixed the first failure |
| Rules written into the prompt as definitions, **without** worked examples | Include the rules file's examples; few-shot | The examples are near-copies of main-set items, so they would leak answers and inflate the score |
| 3 retrieved neighbors | 10, or the whole 30-item set | Measured: k=3 scored 0.553, the whole set scored 0.447 (3 runs each) |
| Temperature 0, fixed seed, `think` off | Higher temperature; model reasoning on | Repeatability for fair comparison; reasoning-on is left as a separate future experiment so cause and effect stay clear |
| Pair-level scoring, no partial credit | Credit for the right requirement with the wrong category | Simple, strict, easy to explain; the cost is that boundary cases between AMB and UNT are punished |
| n8n workflow generated from the Python prompt | Hand-built workflow | One source of truth; the two paths cannot drift. They produced identical findings |
| Different model as judge from the one that writes fixes | Same model | Avoid a model preferring its own style |

## 7. What went wrong (and why it matters)

1. **First baseline: F1 0.000.** The model flagged 1 of 30 requirements. I checked that this was a real result and not a bug (the same model flagged these requirements when asked a slightly different way), then traced it to the output format forcing an early "clean" verdict. One change fixed it, and the log shows the effect.
2. **The fix over-corrected.** After removing the verdict field, the agent flagged 25 of 30 requirements, including 10 of the 11 clean ones. Its F1 (0.320) was *below* the flag-everything baseline. Adding the written rules fixed most of it (0.553).
3. **More context made things worse.** Showing the model the whole set instead of 3 neighbors lowered the score. The cause has not been isolated; one hypothesis is that a small model gets distracted by long context.
4. **Silent CPU fallback.** After a kernel update the NVIDIA driver module was missing, and Ollama quietly used the CPU. It stayed on CPU even after the driver was repaired until the service restarted. Only a status command revealed it. Every run now records how much ran on the GPU.
5. **The AI judge failed its check.** See below.
6. **Process slips, logged openly:** a model download size taken from a third-party source was wrong (9.6 GB claimed, 6.6 GB actual), and one change was applied twice because the repository history wasn't checked first.

### The fix-quality judge

An AI can grade the *quality of suggested fixes*, which have no exact right answer. But an AI grader can be lenient or biased, so it was compared with my own grades on 20 fixes. Raw agreement was 65%, which looks fine, but the judge gave the top grade to 19 of 20 and I did so for 12. Correcting for chance agreement (Cohen's kappa) gives **0.15, which is slight agreement.** The judge cannot tell good fixes from mediocre ones, so **no judge score is reported as a quality figure.** Catching this before using the judge is the reason for the check.

## 8. Operations and architecture notes

- **Where it runs:** one workstation (Ryzen 7 7800X3D, 32 GB RAM, RTX 3080 with 10 GB). All three models are about 4-bit-quantized builds of 7.5 to 8.8 billion parameters and fit on the GPU. Ollama (models) runs on the host; Qdrant (vector database) and n8n (workflow engine) run in Docker.
- **Data privacy:** requirements are processed locally. After the one-time model download, the pipeline makes no external calls.
- **n8n** is the orchestration layer: it receives a requirement over HTTP, calls the embedding model, the vector database and the language model in sequence, and returns findings. Think of it as the pipeline runner for AI work. The Python path and the n8n path produced identical findings on the main set, so orchestration adds no behavioral change.
- **Context window:** set explicitly to 8,192 tokens. Ollama's default of 4,096 silently truncates long prompts, which would look like model degradation in the scores.
- **Reproducibility:** each run folder records the model, prompt version, settings, GPU fraction and wall time. Repeat runs at temperature 0 and a fixed seed were identical for two of the three models; granite varied slightly (F1 standard deviation 0.04).

## 9. Limitations and risks

- **Small samples.** 30 requirements per set, 17 to 19 real defects. Results are directional, not statistically strong.
- **Two different labelers.** The main set is labeled by me and the test set by Claude. A gap between the two sets can partly be labeler differences, not only model performance.
- **Synthetic text.** Both sets are tidier than real project documents, so real-world scores would probably be lower.
- **Not yet checked: my own label consistency.** Re-labeling 10 requirements after 48 hours is planned.
- **One shared index.** Each run rebuilds a single Qdrant collection from the file it processes, so the collection reflects whichever requirements file was indexed last, and the n8n workflow retrieves from that. A production design would use one collection per document. This is a known shortcut.
- **Set-level gaps are out of scope.** The agent checks each requirement; it cannot say "the document is missing a security section."
- **Not production-ready:** no authentication, no monitoring, no handling of large documents or multiple users.

## 10. Where it could go next

- Retry the fix-quality judge with a stricter rubric, checked on a fresh sample of fixes
- Run the sealed test against real requirements (for example, sentences from the public PURE dataset) labeled by me
- Test whether the model's built-in reasoning improves results, as a separate controlled experiment
- Investigate why extra context hurt
- Add a downstream agent that turns accepted requirements into test cases, and write findings to a ticketing system

## 11. Glossary

- **Embedding:** a list of numbers representing the meaning of a text; similar meanings sit close together.
- **Vector database (Qdrant):** a database that finds the stored items closest in meaning to a query.
- **RAG (retrieval-augmented generation):** fetching relevant text first and giving it to the model as context.
- **Structured output:** forcing the model's reply to match a defined data shape.
- **Precision / recall / F1:** see section 4.
- **Dev set / test set:** the set used while tuning, and a separate sealed set used once at the end to check the tuning did not just fit the first set.
- **Overfitting:** doing well on the data you tuned against and worse on new data.
- **LLM-as-judge:** using one AI model to grade another's output. Needs a calibration check against human grades.
- **Cohen's kappa:** agreement between two graders after removing the agreement expected by chance. 0 means chance level, 1 means perfect.
- **Quantization (Q4_K_M):** storing a model's numbers at lower precision so it fits in less memory.
- **Temperature:** a setting controlling randomness; 0 makes output as repeatable as possible.
