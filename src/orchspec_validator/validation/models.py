"""Validation models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ValidationIssue:
    code: str
    message: str
    path: str


@dataclass
class ValidationReport:
    valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    schema_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "valid": self.valid,
                "error_count": len(self.errors),
                "warning_count": len(self.warnings),
                "schema_version": self.schema_version,
            },
            "errors": [asdict(e) for e in self.errors],
            "warnings": [asdict(w) for w in self.warnings],
        }
