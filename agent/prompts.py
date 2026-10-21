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

PROMPTS = {"v0": (V0_SYSTEM, v0_user), "v1": (V1_SYSTEM, v0_user)}
