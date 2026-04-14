"""Decision tree models: nodes, verdicts, evidence, and dissent."""

from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from hexmind.models.round import Round


class NodeStatus(str, Enum):
    ACTIVE = "active"
    CONVERGED = "converged"
    CANCELLED = "cancelled"


class EvidenceItem(BaseModel):
    """A factual data point from White Hat output."""

    id: str  # "W1", "W5"
    content: str
    source_type: str  # "domain" | "web" | "local_file" | "paper"
    source_ref: str | None = None  # URL / DOI / file path


class Dissent(BaseModel):
    """A recorded disagreement by a persona."""

    persona_id: str
    position: str
    reasoning: str
    evidence_refs: list[str] = []


class Verdict(BaseModel):
    """Conclusion of a discussion node."""

    summary: str
    confidence: Literal["high", "medium", "low"]
    key_facts: list[str]
    key_risks: list[str]
    key_values: list[str]
    mitigations: list[str]
    intuition_summary: str
    blue_hat_ruling: str
    next_actions: list[str]
    partial: bool = False  # True if discussion was cancelled
    bibliography: str = ""  # Phase 4: rendered reference list


class DecisionSummary(BaseModel):
    """
    Structured decision summary — auto-extracted from discussion.

    Phase 2: 3 layers (question → analysis → conclusion + dissent).
    Phase 3-5: progressively enriched to full 9 layers.
    """

    # Layer 1: Problem definition
    question: str

    # Layer 2: Analysis (aggregated from hat outputs)
    options: list[str] = []
    benefits: dict[str, list[str]] = {}
    costs: dict[str, list[str]] = {}
    risks: list[str] = []
    evidence: list[EvidenceItem] = []

    # Layer 3: Conclusion
    decision: str
    reasoning: str
    dissents: list[Dissent] = []
    confidence: Literal["high", "medium", "low"]
    next_actions: list[str] = []

    # Layer 4: Retrospective (Phase 2 placeholder, Phase 5 fills)
    outcome: Literal["pending", "correct", "partially_correct", "incorrect"] = "pending"
    outcome_notes: str = ""


class TreeNode(BaseModel):
    """A node in the decision tree (root = main question, children = sub-questions)."""

    id: str = Field(default_factory=lambda: f"node_{uuid4().hex[:8]}")
    question: str
    depth: int = 0
    status: NodeStatus = NodeStatus.ACTIVE
    rounds: list[Round] = []
    children: list["TreeNode"] = []
    verdict: Verdict | None = None
    parent_id: str | None = None
    compressed_context: str | None = None
