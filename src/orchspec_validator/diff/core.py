"""Semantic comparison primitives."""

from __future__ import annotations

from typing import Any

from orchspec_validator.diff.models import DiffItem


def _keyed(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items if item.get("id")}


def _classify(path: str) -> str:
    if path.startswith("components") or path.startswith("flow"):
        return "breaking"
    if path.startswith("integrations"):
        return "non_breaking"
    return "informational"


def _diff_fields(prefix: str, left: Any, right: Any) -> list[DiffItem]:
    changes: list[DiffItem] = []
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left.keys()) | set(right.keys())):
            next_prefix = f"{prefix}.{key}" if prefix else key
            if key not in left:
                changes.append(DiffItem("added", next_prefix, None, right[key], _classify(next_prefix)))
            elif key not in right:
                changes.append(DiffItem("removed", next_prefix, left[key], None, _classify(next_prefix)))
            else:
                changes.extend(_diff_fields(next_prefix, left[key], right[key]))
        return changes

    if left != right:
        changes.append(DiffItem("modified", prefix, left, right, _classify(prefix)))
    return changes


def semantic_diff_impl(left: dict[str, Any], right: dict[str, Any]) -> list[DiffItem]:
    changes: list[DiffItem] = []

    for field in ("pipeline_id", "description", "orchspec_version"):
        lv = left.get(field)
        rv = right.get(field)
        if lv != rv:
            changes.append(DiffItem("modified", field, lv, rv, _classify(field)))

    left_components = _keyed(left.get("components", []))
    right_components = _keyed(right.get("components", []))
    for cid in sorted(set(left_components) | set(right_components)):
        base = f"components.{cid}"
        if cid not in right_components:
            changes.append(DiffItem("removed", base, left_components[cid], None, "breaking"))
        elif cid not in left_components:
            changes.append(DiffItem("added", base, None, right_components[cid], "breaking"))
        else:
            changes.extend(_diff_fields(base, left_components[cid], right_components[cid]))

    left_integrations = _keyed(left.get("integrations", []))
    right_integrations = _keyed(right.get("integrations", []))
    for iid in sorted(set(left_integrations) | set(right_integrations)):
        base = f"integrations.{iid}"
        if iid not in right_integrations:
            changes.append(DiffItem("removed", base, left_integrations[iid], None, "non_breaking"))
        elif iid not in left_integrations:
            changes.append(DiffItem("added", base, None, right_integrations[iid], "non_breaking"))
        else:
            changes.extend(_diff_fields(base, left_integrations[iid], right_integrations[iid]))

    l_edges = {
        (e.get("from"), e.get("to"), e.get("edge_type", "success"))
        for e in left.get("flow", {}).get("edges", [])
    }
    r_edges = {
        (e.get("from"), e.get("to"), e.get("edge_type", "success"))
        for e in right.get("flow", {}).get("edges", [])
    }

    for e in sorted(l_edges - r_edges):
        changes.append(DiffItem("removed", "flow.edges", e, None, "breaking"))
    for e in sorted(r_edges - l_edges):
        changes.append(DiffItem("added", "flow.edges", None, e, "breaking"))

    return changes
