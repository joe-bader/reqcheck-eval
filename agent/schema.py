"""Shape of the model's reply. Ollama enforces this JSON schema while generating."""
from typing import Literal

from pydantic import BaseModel


class Finding(BaseModel):
    category: Literal["AMB", "UNT", "GAP"]
    evidence: str  # quote from the requirement text
    suggested_fix: str


class Review(BaseModel):
    # verdict comes first so the model commits to clean/defective before listing findings
    verdict: Literal["clean", "defective"]
    findings: list[Finding]
