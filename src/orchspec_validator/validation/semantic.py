"""Semantic validation rules for OrchSpec v1.0."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from orchspec_validator.validation.models import ValidationIssue


def _component_ids(doc: dict[str, Any]) -> list[str]:
    return [c.get("id") for c in doc.get("components", []) if c.get("id")]


def _integration_ids(doc: dict[str, Any]) -> list[str]:
    return [i.get("id") for i in doc.get("integrations", []) if i.get("id")]


def _build_graph(components: list[str], edges: list[dict[str, Any]]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    out_graph: dict[str, list[str]] = {cid: [] for cid in components}
    undirected: dict[str, list[str]] = {cid: [] for cid in components}
    for edge in edges:
        src = edge.get("from")
        dst = edge.get("to")
        if src in out_graph and dst in out_graph:
            out_graph[src].append(dst)
            undirected[src].append(dst)
            undirected[dst].append(src)
    return out_graph, undirected


def validate_semantics(
    doc: dict[str, Any], *, strict: bool = False
) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    components = _component_ids(doc)
    component_set = set(components)
    integrations = _integration_ids(doc)
    integration_set = set(integrations)

    entry_points = doc.get("flow", {}).get("entry_points", [])
    for ep in entry_points:
        if ep not in component_set:
            errors.append(ValidationIssue("SEM001", f"entry point '{ep}' not found", "$.flow.entry_points"))

    edges = doc.get("flow", {}).get("edges", [])
    for idx, edge in enumerate(edges):
        if edge.get("from") not in component_set or edge.get("to") not in component_set:
            errors.append(
                ValidationIssue("SEM002", "edge references unknown component", f"$.flow.edges[{idx}]")
            )

    pattern = doc.get("flow", {}).get("pattern")
    out_graph, undirected = _build_graph(components, edges)

    if pattern in {"sequential", "parallel", "dag"}:
        indeg: dict[str, int] = {cid: 0 for cid in components}
        for src in components:
            for dst in out_graph[src]:
                indeg[dst] += 1

        q = deque([n for n in components if indeg[n] == 0])
        seen = 0
        while q:
            n = q.popleft()
            seen += 1
            for nxt in out_graph[n]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        if seen != len(components):
            errors.append(ValidationIssue("SEM003", "flow contains cycle", "$.flow.edges"))

    for idx, comp in enumerate(doc.get("components", [])):
        for integration in comp.get("integrations_used", []):
            if integration not in integration_set:
                errors.append(
                    ValidationIssue(
                        "SEM004",
                        f"component integration '{integration}' not declared",
                        f"$.components[{idx}].integrations_used",
                    )
                )
        for io_idx, io in enumerate((comp.get("inputs") or []) + (comp.get("outputs") or [])):
            integration_id = io.get("integration_id")
            if integration_id and integration_id not in integration_set:
                errors.append(
                    ValidationIssue(
                        "SEM005",
                        f"io integration '{integration_id}' not declared",
                        f"$.components[{idx}].io[{io_idx}]",
                    )
                )

    secret_set = {s.get("name") for s in doc.get("secrets", []) if s.get("name")}
    for idx, integ in enumerate(doc.get("integrations", [])):
        auth = integ.get("authentication") or {}
        for secret_key in ("secret_ref", "username_secret", "password_secret"):
            secret_name = auth.get(secret_key)
            if secret_name and secret_name not in secret_set:
                errors.append(
                    ValidationIssue(
                        "SEM006",
                        f"integration secret '{secret_name}' not declared",
                        f"$.integrations[{idx}].authentication.{secret_key}",
                    )
                )

    if len(component_set) != len(components):
        errors.append(ValidationIssue("SEM007", "duplicate component ids", "$.components"))
    if len(integration_set) != len(integrations):
        errors.append(ValidationIssue("SEM007", "duplicate integration ids", "$.integrations"))

    if pattern == "sequential":
        fanout: dict[str, int] = defaultdict(int)
        for edge in edges:
            fanout[edge.get("from", "")] += 1
        offenders = [node for node, count in fanout.items() if count > 1]
        if offenders:
            errors.append(
                ValidationIssue(
                    "SEM008",
                    f"sequential flow has branching nodes: {', '.join(sorted(offenders))}",
                    "$.flow.edges",
                )
            )

    schedule = doc.get("schedule") or {}
    if schedule.get("enabled") and not schedule.get("cron"):
        errors.append(ValidationIssue("SEM009", "schedule enabled requires cron", "$.schedule"))

    allowed = {
        "Extractor": {"python_script", "http_request", "container", "bash", "sql", "custom"},
        "Transformer": {"python_script", "sql", "bash", "container", "custom"},
        "Loader": {"python_script", "sql", "container", "bash", "http_request", "custom"},
        "QualityCheck": {"python_script", "sql", "bash", "custom"},
        "Notifier": {"email", "http_request", "python_script", "custom"},
        "Sensor": {"http_request", "python_script", "custom"},
        "Reconciliator": {"python_script", "sql", "container", "custom"},
        "Custom": {"custom", "python_script", "container", "bash", "sql", "http_request", "email"},
    }
    for idx, comp in enumerate(doc.get("components", [])):
        category = comp.get("category")
        executor = (comp.get("executor") or {}).get("type")
        if category in allowed and executor and executor not in allowed[category]:
            issue = ValidationIssue(
                "SEM010",
                f"category '{category}' incompatible with executor '{executor}'",
                f"$.components[{idx}]",
            )
            if strict:
                errors.append(issue)
            else:
                warnings.append(issue)

    # SEM011: all components should be reachable from entry points.
    reachable: set[str] = set()
    q = deque([ep for ep in entry_points if ep in component_set])
    while q:
        node = q.popleft()
        if node in reachable:
            continue
        reachable.add(node)
        for nxt in out_graph.get(node, []):
            q.append(nxt)
    unreachable = sorted(component_set - reachable)
    if unreachable:
        errors.append(
            ValidationIssue(
                "SEM011",
                f"unreachable components from entry_points: {', '.join(unreachable)}",
                "$.flow",
            )
        )

    # SEM012: graph should be a single weakly connected component.
    if components:
        seen: set[str] = set()
        groups = 0
        for start in components:
            if start in seen:
                continue
            groups += 1
            qq = deque([start])
            while qq:
                node = qq.popleft()
                if node in seen:
                    continue
                seen.add(node)
                for nxt in undirected.get(node, []):
                    qq.append(nxt)
        if groups > 1:
            errors.append(
                ValidationIssue(
                    "SEM012",
                    f"flow has disconnected subgraphs ({groups} groups)",
                    "$.flow.edges",
                )
            )

    # SEM013: retry configuration coherence.
    for idx, comp in enumerate(doc.get("components", [])):
        retry = comp.get("retry") or {}
        strategy = retry.get("strategy")
        delay = retry.get("delay_seconds")
        max_delay = retry.get("max_delay_seconds")
        multiplier = retry.get("multiplier")

        if strategy == "exponential":
            if multiplier is not None and multiplier <= 1:
                errors.append(
                    ValidationIssue(
                        "SEM013",
                        "exponential retry requires multiplier > 1",
                        f"$.components[{idx}].retry.multiplier",
                    )
                )
            if delay is not None and max_delay is not None and max_delay < delay:
                errors.append(
                    ValidationIssue(
                        "SEM013",
                        "max_delay_seconds must be >= delay_seconds",
                        f"$.components[{idx}].retry.max_delay_seconds",
                    )
                )

    return errors, warnings
