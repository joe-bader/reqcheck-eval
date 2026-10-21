# Matching and scoring rules (v1)

## What gets compared

Both sides are reduced to a **set of `(req_id, category)` pairs**.

- Gold: one pair per distinct category on each requirement in the labeled file.
- Predicted: one pair per distinct `(req_id, category)` in the agent's findings. Several findings with the same pair collapse to one, so an agent can't raise its score by repeating itself.

Evidence quotes and suggested fixes are **not** compared in v1. A finding is a true positive only if both `req_id` and `category` match.

## Counts

- **TP**: pair in both sets.
- **FP**: predicted pair not in gold. This includes the right requirement with the wrong category (no partial credit), a flag on a clean requirement, and any pair with an unknown `req_id` or category (these are also listed as warnings).
- **FN**: gold pair the agent did not predict.
- True negatives are not counted. Most pairs are not defects, so accuracy would look good for an agent that flags nothing.

## Metrics

- Precision = TP / (TP + FP): of what the agent flagged, how much was real.
- Recall = TP / (TP + FN): of the real defects, how many the agent found.
- F1 = harmonic mean of the two. It is low if either one is low.
- Reported overall and per category. **Overall is micro-averaged**: TP/FP/FN are pooled over all pairs before computing the ratios, so larger categories weigh more.
- A metric with an empty denominator is reported as `n/a`, not 0 (for example, precision when the agent made no findings).

## Known limits

- With about 30 requirements and a handful of labels per category, one pair moves a per-category score a lot. Treat differences of a few points as noise until repeat runs say otherwise.
- Category-only matching can't tell whether the agent flagged the right words. Evidence-level checking is a possible v2.
- `borderline: true` labels count the same as any other. Scoring them separately is a possible follow-up.
- Set-level gaps (whole missing requirements) are out of scope; see the labeling rules.

## Changelog

- v1: initial rules.
