"""Semantic validation rules for OrchSpec v1.0."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Any

from orchspec_validator.validation.models import ValidationIssue


# ---------------------------------------------------------------------------
# Resource parsing helpers (SEM014)
# ---------------------------------------------------------------------------

_CPU_RE = re.compile(r"^(\d+(?:\.\d+)?)(m?)$")
_MEM_RE = re.compile(r"^(\d+(?:\.\d+)?)(Ki|Mi|Gi|Ti|K|M|G|T)?$")
_MEM_UNITS: dict[str, int] = {
    "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40,
    "K": 1000, "M": 1000**2, "G": 1000**3, "T": 1000**4,
}


def _parse_cpu(raw: str) -> float | None:
    """Parse a CPU resource string into millicores. Returns None on failure."""
    m = _CPU_RE.match(str(raw).strip())
    if not m:
        return None
    value = float(m.group(1))
    if m.group(2) == "m":
        return value
    return value * 1000  # cores → millicores


def _parse_memory(raw: str) -> int | None:
    """Parse a memory resource string into bytes. Returns None on failure."""
    m = _MEM_RE.match(str(raw).strip())
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2)
    if unit is None:
        return int(value)  # assume bytes
    return int(value * _MEM_UNITS[unit])


# ---------------------------------------------------------------------------
# IO kind ↔ integration type compatibility matrix (SEM019)
# ---------------------------------------------------------------------------

_KIND_INTEGRATION_COMPAT: dict[str, set[str]] = {
    "file": {"filesystem", "object_store"},
    "table": {"database"},
    "api": {"api"},
    "object": {"object_store", "filesystem"},
    "stream": {"message_queue", "api"},
    "secret": {"api", "database", "filesystem", "object_store", "message_queue", "smtp", "custom"},
    "volume": {"filesystem"},
}


# ---------------------------------------------------------------------------
# ISO 8601 duration parser (SEM020)
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")


def _parse_duration_seconds(raw: str) -> int | None:
    """Parse ISO 8601 duration (PT1H30M10S) into total seconds."""
    m = _DURATION_RE.match(str(raw).strip())
    if not m:
        return None
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    if h == 0 and mi == 0 and s == 0:
        return None
    return h * 3600 + mi * 60 + s


# ---------------------------------------------------------------------------
# Cron-to-minimum-interval estimator (SEM020)
# ---------------------------------------------------------------------------

_CRON_PARTS_RE = re.compile(r"^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$")


def _cron_min_interval_minutes(cron: str) -> int | None:
    """Estimate the minimum interval (in minutes) of a cron expression.
    Returns None for complex or unparseable expressions."""
    m = _CRON_PARTS_RE.match(str(cron).strip())
    if not m:
        return None
    minute, hour, dom, month, dow = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)

    if minute.startswith("*/") and minute[2:].isdigit():
        return int(minute[2:])
    if minute == "*" and hour == "*":
        return 1  # every minute
    if minute == "*" and hour.startswith("*/"):
        try:
            return int(hour[2:]) * 60
        except ValueError:
            pass
    if minute.isdigit() and hour == "*":
        return 60  # hourly at a specific minute
    return None  # daily or complex — not a concern


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


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

    # --- SEM014: resource requests must not exceed limits per component ---
    for idx, comp in enumerate(doc.get("components", [])):
        resources = comp.get("resources") or {}
        req = resources.get("request") or {}
        lim = resources.get("limit") or {}

        for rtype, label in [("cpu", "CPU"), ("memory", "memory")]:
            req_val = req.get(rtype)
            lim_val = lim.get(rtype)
            if not req_val or not lim_val:
                continue
            parser = _parse_cpu if rtype == "cpu" else _parse_memory
            req_parsed = parser(str(req_val))
            lim_parsed = parser(str(lim_val))
            if req_parsed is not None and lim_parsed is not None and req_parsed > lim_parsed:
                errors.append(
                    ValidationIssue(
                        "SEM014",
                        f"{label} request ({req_val}) exceeds limit ({lim_val})",
                        f"$.components[{idx}].resources",
                    )
                )
        gpu_req = req.get("gpu")
        gpu_lim = lim.get("gpu")
        if (
            isinstance(gpu_req, (int, float))
            and isinstance(gpu_lim, (int, float))
            and gpu_req > gpu_lim
        ):
            errors.append(
                ValidationIssue(
                    "SEM014",
                    f"GPU request ({gpu_req}) exceeds limit ({gpu_lim})",
                    f"$.components[{idx}].resources",
                )
            )

    # --- SEM015: security context coherence ---
    for section_name, section_path in [
        ("container_runtime", "$.container_runtime"),
    ]:
        section = doc.get(section_name) or {}
        sec_ctx = section.get("security_context") or {}
        if sec_ctx:
            _check_security_context(sec_ctx, section_path, errors)
    for idx, comp in enumerate(doc.get("components", [])):
        sec_ctx = comp.get("security_context") or {}
        if sec_ctx:
            _check_security_context(sec_ctx, f"$.components[{idx}].security_context", errors)

    # --- SEM016: duplicate output path conflicts ---
    output_paths: dict[str, list[int]] = defaultdict(list)
    for idx, comp in enumerate(doc.get("components", [])):
        for io_item in comp.get("outputs") or []:
            path_pat = io_item.get("path_pattern")
            if path_pat and str(path_pat).strip():
                output_paths[str(path_pat).strip()].append(idx)
    for path_pat, comp_indices in output_paths.items():
        if len(comp_indices) > 1:
            cids = [doc["components"][i]["id"] for i in comp_indices]
            warnings.append(
                ValidationIssue(
                    "SEM016",
                    f"output path '{path_pat}' written by multiple components: {', '.join(cids)}",
                    "$.components",
                )
            )

    # --- SEM017: data flow compatibility between connected components ---
    comp_by_id = {c["id"]: c for c in doc.get("components", [])}
    for edge in edges:
        src_id = edge.get("from")
        dst_id = edge.get("to")
        src = comp_by_id.get(src_id, {})
        dst = comp_by_id.get(dst_id, {})
        src_output_kinds = {
            io.get("kind") for io in (src.get("outputs") or []) if io.get("kind")
        }
        dst_input_kinds = {
            io.get("kind") for io in (dst.get("inputs") or []) if io.get("kind")
        }
        if src_output_kinds and dst_input_kinds:
            overlap = src_output_kinds & dst_input_kinds
            if not overlap:
                warnings.append(
                    ValidationIssue(
                        "SEM017",
                        f"edge {src_id}→{dst_id}: source outputs {sorted(src_output_kinds)} "
                        f"have no overlap with target inputs {sorted(dst_input_kinds)}",
                        "$.flow.edges",
                    )
                )

    # --- SEM018: condition expression syntax ---
    for idx, edge in enumerate(edges):
        condition = edge.get("condition")
        if condition is None:
            continue
        cond_str = str(condition).strip()
        if not cond_str:
            warnings.append(
                ValidationIssue(
                    "SEM018",
                    f"edge {edge.get('from')}→{edge.get('to')} has empty condition",
                    f"$.flow.edges[{idx}].condition",
                )
            )
            continue
        # check balanced parentheses
        parens = 0
        brackets = 0
        for ch in cond_str:
            if ch == '(':
                parens += 1
            elif ch == ')':
                parens -= 1
            elif ch == '[':
                brackets += 1
            elif ch == ']':
                brackets -= 1
        if parens != 0:
            warnings.append(
                ValidationIssue(
                    "SEM018",
                    f"edge {edge.get('from')}→{edge.get('to')}: unbalanced parentheses in condition '{cond_str}'",
                    f"$.flow.edges[{idx}].condition",
                )
            )
        if brackets != 0:
            warnings.append(
                ValidationIssue(
                    "SEM018",
                    f"edge {edge.get('from')}→{edge.get('to')}: unbalanced brackets in condition '{cond_str}'",
                    f"$.flow.edges[{idx}].condition",
                )
            )

    # --- SEM019: integration type ↔ IO kind compatibility ---
    integ_by_id = {i["id"]: i for i in doc.get("integrations", []) if i.get("id")}
    for idx, comp in enumerate(doc.get("components", [])):
        all_io = (comp.get("inputs") or []) + (comp.get("outputs") or [])
        for io_idx, io_item in enumerate(all_io):
            integration_id = io_item.get("integration_id")
            io_kind = io_item.get("kind")
            if not integration_id or not io_kind:
                continue
            integration = integ_by_id.get(integration_id)
            if not integration:
                continue
            integ_type = integration.get("type")
            if not integ_type:
                continue
            compat_kinds = _KIND_INTEGRATION_COMPAT.get(io_kind)
            if compat_kinds and integ_type not in compat_kinds:
                warnings.append(
                    ValidationIssue(
                        "SEM019",
                        f"IO kind '{io_kind}' is incompatible with integration type '{integ_type}' "
                        f"(expected one of: {sorted(compat_kinds)})",
                        f"$.components[{idx}].io[{io_idx}]",
                    )
                )

    # --- SEM020: timeout vs schedule interval sanity ---
    schedule = doc.get("schedule") or {}
    if schedule.get("enabled") and schedule.get("cron"):
        cron_interval_min = _cron_min_interval_minutes(str(schedule["cron"]))
        if cron_interval_min is not None:
            cron_interval_sec = cron_interval_min * 60
            for idx, comp in enumerate(doc.get("components", [])):
                timeout_str = comp.get("timeout")
                if not timeout_str:
                    continue
                timeout_sec = _parse_duration_seconds(str(timeout_str))
                if timeout_sec is not None and timeout_sec > cron_interval_sec:
                    warnings.append(
                        ValidationIssue(
                            "SEM020",
                            f"component '{comp['id']}' timeout ({timeout_str} ≈ {timeout_sec}s) "
                            f"exceeds schedule interval (~{cron_interval_sec}s); "
                            f"component may not complete before next scheduled run",
                            f"$.components[{idx}].timeout",
                        )
                    )

    # --- SEM021: unused parameters and secrets ---
    declared_params = set(doc.get("parameters", {}).keys())
    if declared_params:
        used_params: set[str] = set()
        for comp in doc.get("components", []):
            comp_params = comp.get("parameters") or {}
            if isinstance(comp_params, dict):
                used_params |= set(comp_params.keys())
        unused = sorted(declared_params - used_params)
        if unused:
            warnings.append(
                ValidationIssue(
                    "SEM021",
                    f"parameters declared but not consumed by any component: {', '.join(unused)}",
                    "$.parameters",
                )
            )

    declared_secrets = {s["name"] for s in doc.get("secrets", []) if s.get("name")}
    if declared_secrets:
        used_secrets: set[str] = set()
        for integ in doc.get("integrations", []):
            auth = integ.get("authentication") or {}
            for sk in ("secret_ref", "username_secret", "password_secret"):
                sv = auth.get(sk)
                if sv:
                    used_secrets.add(sv)
        for comp in doc.get("components", []):
            env = comp.get("env") or {}
            if isinstance(env, dict):
                for env_val in env.values():
                    if isinstance(env_val, str) and env_val.startswith("$SECRET:"):
                        used_secrets.add(env_val[len("$SECRET:"):])
        unused_sec = sorted(declared_secrets - used_secrets)
        if unused_sec:
            warnings.append(
                ValidationIssue(
                    "SEM021",
                    f"secrets declared but not referenced by any integration or component: {', '.join(unused_sec)}",
                    "$.secrets",
                )
            )

    return errors, warnings


def _check_security_context(
    sec_ctx: dict[str, Any], path: str, errors: list[ValidationIssue]
) -> None:
    run_as_non_root = sec_ctx.get("run_as_non_root")
    run_as_user = sec_ctx.get("run_as_user")
    if run_as_non_root is True and run_as_user == 0:
        errors.append(
            ValidationIssue(
                "SEM015",
                "run_as_non_root is true but run_as_user is 0 (root)",
                path,
            )
        )

    drops = set(sec_ctx.get("drop_capabilities") or [])
    adds = set(sec_ctx.get("add_capabilities") or [])
    conflicts = drops & adds
    if conflicts:
        errors.append(
            ValidationIssue(
                "SEM015",
                f"capabilities both dropped and added: {', '.join(sorted(conflicts))}",
                path,
            )
        )
