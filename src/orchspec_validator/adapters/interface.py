"""Adapter protocol for OrchSpec projection layers."""

from __future__ import annotations

from typing import Protocol

from orchspec_validator.adapters.models import AdapterCapability, ProjectionResult


class OrchspecAdapter(Protocol):
    def capability(self) -> AdapterCapability:
        """Return adapter capability metadata."""

    def validate_invariants(self, orchspec_doc: dict) -> list[str]:
        """Validate projection invariants; return list of violations."""

    def project(self, orchspec_doc: dict) -> ProjectionResult:
        """Project OrchSpec into target-specific IR (stub in v1)."""
