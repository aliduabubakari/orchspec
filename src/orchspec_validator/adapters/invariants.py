"""Shared invariants for target adapters."""

from __future__ import annotations

from typing import Any

from orchspec_validator.compiler.mapping_spec import orchestrator_invariants


def validate_projection_invariants(orchspec_doc: dict[str, Any]) -> list[str]:
    rules = orchestrator_invariants()
    violations: list[str] = []

    pipeline_id = orchspec_doc.get("pipeline_id")
    if not pipeline_id:
        violations.append("missing pipeline_id")

    metadata = orchspec_doc.get("metadata") or {}
    if not metadata.get("name"):
        violations.append("missing metadata.name")

    components = orchspec_doc.get("components") or []
    if not components:
        violations.append("missing components")
    for idx, comp in enumerate(components):
        if not comp.get("id"):
            violations.append(f"component[{idx}] missing id")
        if not (comp.get("executor") or {}).get("type"):
            violations.append(f"component[{idx}] missing executor.type")

    flow = orchspec_doc.get("flow") or {}
    if not flow.get("pattern"):
        violations.append("missing flow.pattern")
    if "edges" not in flow:
        violations.append("missing flow.edges")

    # Sanity-check config itself so adapter authors can rely on it.
    for group in ("imperative_targets", "declarative_targets"):
        if not isinstance(rules.get(group), list):
            violations.append(f"mapping spec missing '{group}' list")

    return violations
