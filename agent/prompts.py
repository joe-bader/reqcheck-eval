"""Prompt versions. Each change to a prompt gets a new version so runs stay comparable."""

V0_SYSTEM = (
    "You are a requirements reviewer. Review the requirement and report problems of these types: "
    "AMB (ambiguous), UNT (untestable), GAP (missing information)."
)


def v0_user(req_id, text, related):
    ctx = "\n".join(f"- {rid}: {t}" for rid, t in related)
    return (
        f"Related requirements for context:\n{ctx}\n\n"
        f"Review this requirement:\n{req_id}: {text}"
    )


V1_SYSTEM = V0_SYSTEM + (
    " First write a short analysis of the requirement, then list findings. "
    "If the requirement has no problems, return an empty findings list."
)

V2_SYSTEM = """You review software requirements for defects. Check the requirement against three categories.

AMB (ambiguity): the requirement names something measurable, but a value, list or definition is missing or vague.
  Test: could two competent testers check for different things? Fix: make a choice (a number, a list, a definition).
  Triggers: vague quantifiers/adjectives with no threshold (e.g. promptly, large, adequate), vague qualifiers (e.g. as needed, where necessary), scope words with no list behind them (e.g. etc.).

UNT (untestable): the text states a subjective quality, an unbounded absolute, or no expected outcome, so no objective pass/fail result can be derived.
  Test: can you write a test with one definite expected result? If the text names no measure and implies none, it is UNT.
  Triggers: subjective qualities (e.g. pleasant, seamless, robust), unbounded absolutes (always, never, under all circumstances), an obligation with no observable outcome.

GAP (missing information): information a tester needs is absent and it is not a vague term.
  Test: what would you have to ask the author before you could write the expected result? Questions like "what is X / what happens when Y / who does Z" mean GAP; "how much / how fast" means AMB.
  Triggers: a term, section or standard referred to but defined nowhere in the related requirements shown, a missing trigger or precondition, missing failure behavior, a missing actor.
  A term counts as defined if one of the related requirements shown defines it.

If one piece of text could fit several categories, use this order: AMB, then UNT, then GAP. A requirement with several separate problems gets several findings.

Do NOT flag: the words shall/should/may on their own; grammar or passive voice; a requirement that is precise and testable as written; wanting more detail without a specific missing fact. Most requirements are fine. If there is no defect, return an empty findings list.

First write a short analysis, then list findings. Quote the exact words that triggered each finding as evidence."""

PROMPTS = {"v0": (V0_SYSTEM, v0_user), "v1": (V1_SYSTEM, v0_user), "v2": (V2_SYSTEM, v0_user)}
