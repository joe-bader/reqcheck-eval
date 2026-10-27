# reqcheck-eval in one page

**What it is.** A requirements reviewer that runs on one workstation, with no data leaving the machine. It reads each software requirement and flags three defects, quoting the words at fault and suggesting a fix:

| Defect | Meaning | Example |
|---|---|---|
| Ambiguity | Something measurable is named, but no value | "respond **promptly**" |
| Untestable | Subjective or unlimited wording | "must be **seamless**" |
| Gap | Information a tester needs is absent | "follow **the pharmacy workflow**" (defined nowhere) |

**Why it matters.** A vague requirement lets two people build and test two different things, and the problem surfaces late. Catching it at review time is cheap.

**The real work is the measurement.** Anyone can connect an AI model and get plausible output. The question is whether the output is right, and whether a change made it better or worse. I answered that with a hand-labeled answer key, a deterministic scorer, a sealed second test set, and a log of every experiment, including the failures.

## Does it work?

| | Dev set (my labels) | Sealed test set |
|---|---|---|
| Share of flags that were real (precision) | 61% | 67% |
| Share of real defects caught (recall) | 58% | 94% |
| F1 (one number combining both) | 0.60 | 0.78 |
| Same score for an agent that flags everything | 0.35 | 0.32 |

Best of three local models: gemma4:e4b, at 0.7 seconds per requirement on an RTX 3080. Good enough as a first-pass assistant for a human reviewer; not good enough to run unattended.

Two cautions. Each set has fewer than 20 real defects, so one requirement moves a score by several points; only the large gaps are meaningful. And both sets are synthetic, so real documents would score lower.

## How it works

```
requirement -> find the 3 most similar other requirements (Qdrant vector DB)
            -> prompt: labeling rules + those neighbors + this requirement
            -> local model (Ollama), answer forced into a JSON schema
            -> findings -> scorer -> precision / recall / F1
```

The model reviews every requirement; retrieval only supplies context such as "is this term defined elsewhere?" The same pipeline runs as plain Python and as an n8n workflow generated from the same prompt, and the two produced identical findings.

## What the measurement caught

- **The first version scored zero.** Asking the model for a clean/defective verdict before any reasoning made it say "clean" 29 times out of 30. Letting it reason first fixed that.
- **Over-correction.** The fix made it flag 25 of 30, scoring worse than flagging everything. Putting the written labeling rules into the prompt brought it to 0.55.
- **Overfitting.** I tuned the prompt against one model. On the sealed test set, that model dropped from 0.55 to 0.39 while the other two improved.
- **More context hurt.** Showing the model the whole document instead of 3 neighbors lowered the score. Cause not yet isolated.
- **The AI judge failed.** I tried a second model to grade fix quality, then graded 20 fixes myself. It gave 19 of 20 the top grade; agreement corrected for chance was 0.15, so no judge scores are reported.
- **My own labels held up.** Re-labeling 10 requirements blind five days later matched 29 of 30 decisions (kappa 0.89).

## Limits

Small synthetic samples; one labeler per set (the test set was labeled by Claude, not me); three models of similar size; a single shared vector index; no security, monitoring or multi-user handling. It is a proof of concept.

Details, every number, and the full run history: [README](../README.md), [results/LOG.md](../results/LOG.md).
