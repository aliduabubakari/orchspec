"""Semantic diff for OrchSpec documents."""

from __future__ import annotations

from typing import Any

from orchspec_validator.diff.core import semantic_diff_impl
from orchspec_validator.diff.models import DiffReport


def semantic_diff_orchspec(left: dict[str, Any], right: dict[str, Any]) -> DiffReport:
    return DiffReport(changes=semantic_diff_impl(left, right))
