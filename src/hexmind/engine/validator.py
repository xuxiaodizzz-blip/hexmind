"""OutputValidator: hat constraint enforcement via regex-based checks."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from hexmind.models.hat import HAT_CONSTRAINTS, HatColor
from hexmind.models.persona import Persona
from hexmind.models.round import PanelistOutput


class Violation(BaseModel):
    """A single constraint violation."""

    rule: str
    description: str


class ValidationResult(BaseModel):
    """Result of validating a panelist output against hat constraints."""

    passed: bool
    violations: list[Violation] = Field(default_factory=list)


class OutputValidator:
    """Validate panelist outputs against hat-specific constraints."""

    def validate(
        self,
        output: PanelistOutput,
        hat: HatColor,
        persona: Persona,
    ) -> ValidationResult:
        del persona  # Role prompts stay orthogonal to hat rules.

        violations: list[Violation] = []
        constraint = HAT_CONSTRAINTS[hat]

        violations.extend(
            self._check_prohibited_patterns(
                output.content, constraint.prohibited_patterns
            )
        )
        violations.extend(
            self._check_format(output.content, constraint.required_format)
        )
        violations.extend(
            self._check_max_sentences(output.content, constraint.max_sentences)
        )
        violations.extend(
            self._check_references(output.content, constraint.references_required)
        )

        return ValidationResult(
            passed=len(violations) == 0,
            violations=violations,
        )

    @staticmethod
    def _check_prohibited_patterns(
        content: str, patterns: list[str]
    ) -> list[Violation]:
        violations: list[Violation] = []
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(
                    Violation(
                        rule="prohibited_pattern",
                        description=f"Output contains prohibited pattern: {pattern}",
                    )
                )
        return violations

    @staticmethod
    def _check_format(
        content: str, required_format: str | None
    ) -> list[Violation]:
        if required_format is None:
            return []
        lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
        if not lines:
            return [Violation(rule="format", description="Output is empty")]
        if not any(re.match(required_format, line) for line in lines):
            return [
                Violation(
                    rule="format",
                    description=f"Output does not match required format: {required_format}",
                )
            ]
        return []

    @staticmethod
    def _check_max_sentences(
        content: str, max_sentences: int | None
    ) -> list[Violation]:
        if max_sentences is None:
            return []
        sentences = [
            s for s in re.split(r"[。?!！？\n]", content) if s.strip()
        ]
        if len(sentences) > max_sentences:
            return [
                Violation(
                    rule="max_sentences",
                    description=f"Sentence count {len(sentences)} exceeds limit {max_sentences}",
                )
            ]
        return []

    @staticmethod
    def _check_references(
        content: str, references_required: str | None
    ) -> list[Violation]:
        if references_required is None:
            return []
        ref_prefix = {"white": "W", "black": "B"}[references_required]
        found_refs = re.findall(rf"{ref_prefix}\d+", content)
        if not found_refs:
            return [
                Violation(
                    rule="references",
                    description=f"Missing required {ref_prefix} references",
                )
            ]
        return []
