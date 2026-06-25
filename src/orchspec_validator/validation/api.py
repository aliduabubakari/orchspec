"""Validation API for OrchSpec documents."""

from __future__ import annotations

from typing import Any

from orchspec_validator.validation.models import ValidationReport
from orchspec_validator.validation.schema import validate_against_schema
from orchspec_validator.validation.semantic import validate_semantics


def validate_orchspec(
    doc: dict[str, Any], *, schema_version: str = "1.0", strict: bool = False
) -> ValidationReport:
    errors, warnings = validate_against_schema(doc, schema_version=schema_version)
    sem_errors, sem_warnings = validate_semantics(doc, strict=strict)
    errors.extend(sem_errors)
    warnings.extend(sem_warnings)
    return ValidationReport(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        schema_version=schema_version,
    )
