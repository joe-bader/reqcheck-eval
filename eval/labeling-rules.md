# Labeling rules (v1)

**Status:** written before any labeling and before any agent run. If a rule changes, record it in the changelog at the bottom and re-label every affected item.

## What is being labeled

Each requirement is checked for three defect types. A requirement can carry zero to three labels. The unit of scoring is one `(req_id, category)` pair.

The three categories are mutually exclusive for any one piece of text (see "One span, one label"), so the same wording never counts twice.

## The three categories

### AMBIGUITY (`AMB`)

**Definition:** the requirement names something measurable, but a value, list or definition is missing or vague.

**Test:** could two competent testers read this and check for different things?

**Typical triggers:**
- vague quantifiers and adjectives with no threshold: *quickly, timely, highly, major, appropriately*
- vague qualifiers: *as appropriate, where necessary, if needed, too long*
- scope words with no list behind them: *sensitive, applicable, etc.*
- *and/or* where the two readings change what a tester must verify

**Fix signal:** ambiguity is fixed by making a choice (a number, a list, a definition).

### UNTESTABLE (`UNT`)

**Definition:** the text states a subjective quality, an unbounded absolute, or no expected outcome at all, so no objective pass/fail result can be derived from it.

**Test:** can I write a test with one definite expected result? If the text names no measure and implies none, label `UNT`.

**Typical triggers:**
- subjective qualities: *user-friendly, intuitive, gracefully, robust*
- unbounded absolutes: *never, always, under all circumstances*
- an obligation with no observable outcome

**Fix signal:** untestable requirements need rewriting, not just a number filled in.

### GAP (`GAP`)

**Definition:** information a tester needs is absent, and it is not a vague term (that would be `AMB`).

**Test:** "What would I have to ask the author before I could write the expected result?" If the question is *what is X / what happens when Y / who does Z*, it's a gap. If the question is *how much / how fast*, it's `AMB`.

**Typical triggers:**
- an undefined referent (a term, section or standard the set never defines)
- a missing trigger, precondition or condition
- missing failure or edge behavior
- a missing actor

**Cross-reference rule:** a referent counts as defined if another requirement in the same set defines it. A reference to anything outside the set (another section, an external standard) with no definition inside the set is a gap.

**Scope:** `GAP` is labeled on a specific requirement. Missing *whole* requirements (set-level gaps) are out of scope for v1.

## One span, one label

Every defective piece of text gets exactly one label, by this precedence:

1. It names a measurable property whose value or definition is missing → `AMB`
2. It names a subjective quality, an unbounded absolute, or gives no expected outcome → `UNT`
3. Information is simply absent (not a vague span) → `GAP`

A requirement with several defective spans gets several labels. If two spans earn the same category, it is still one `(req_id, category)` pair.

### Worked examples

| Requirement text | Label(s) | Why |
|---|---|---|
| "Search results should be returned **quickly**." | `AMB` | response time is measurable; the threshold is missing |
| "The system shall be **user-friendly and intuitive**." | `UNT` | subjective, no measure named |
| "The system shall **never lose** customer data." | `UNT` | unbounded absolute; no finite test proves it |
| "Reports shall use **the standard timeout** when generation **takes too long**." | `GAP` + `AMB` | the referent is defined nowhere in the set; "too long" has no threshold |

These are teaching examples, not part of the starter set's answer key.

## Not defects (do not label)

- *shall / should / may* by themselves. Label only if the optionality changes what a tester must verify.
- passive voice, grammar, wording you'd write differently
- compound sentences by themselves. Label the defective half only.
- non-functional requirements you think are missing elsewhere (set-level, out of scope)
- anything you'd call "could be more detailed" without a specific missing fact

## Process rules

1. **Label blind.** Finish labeling before the agent has ever run on the set.
2. **Use only the set.** Judge each requirement from its own text plus the other requirements in the same set. No outside knowledge of the product.
3. **Quote evidence.** Every label carries the exact span that triggered it.
4. **Flag borderline cases.** Set `"borderline": true`, add a one-line note, and decide using these rules anyway.
5. **No relabeling after seeing agent output.** The only exception is a rule change, recorded below, applied to every affected item.
6. **Self-consistency check.** After at least 48 hours, re-label a random 10 requirements without looking at your first labels, and report how often you agreed with yourself.
7. **`null` vs `[]`.** `"labels": null` means not yet labeled. `"labels": []` means labeled and clean.

## Label format

```json
{
  "req_id": "REQ-004",
  "text": "Search results should be returned quickly.",
  "labels": [
    {
      "category": "AMB",
      "evidence": "quickly",
      "borderline": false,
      "note": ""
    }
  ]
}
```

## Matching convention (preview)

A flag from the agent counts as correct if its `req_id` and `category` both match a label. Evidence spans don't have to match in v1. The final rule lives in `eval/matching.md`.

## Changelog

- v1: initial rules.
