"""Deterministic mapping from PipeSpec v1.0 to OPOS v1.0."""

from __future__ import annotations

from collections import deque
import re
from typing import Any

from opos_validator.compiler.mapping_spec import executor_mapping, parameter_type_mapping
from opos_validator.compiler.models import CompileError, CompileOptions
from opos_validator.compiler.profile import validate_pipespec_profile

EXECUTOR_MAP = executor_mapping()
TYPE_MAP = parameter_type_mapping()
INTEGRATION_TYPE_MAP = {
    "api": "api",
    "database": "database",
    "filesystem": "filesystem",
    "file": "filesystem",
    "object_store": "object_store",
    "objectstore": "object_store",
    "message_queue": "message_queue",
    "queue": "message_queue",
    "smtp": "smtp",
    "custom": "custom",
    "other": "custom",
    "ftp": "custom",
}
IO_FORMAT_MAP = {
    "txt": "text",
    "text": "text",
    "json": "json",
    "csv": "csv",
    "parquet": "parquet",
    "avro": "avro",
    "html": "html",
    "sql": "sql",
    "binary": "binary",
}
EDGE_TYPE_MAP = {
    "success": "success",
    "failure": "failure",
    "always": "always",
    "conditional": "success",
}


def _omits_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None and v != {}}


def _require(value: Any, code: str, message: str, path: str) -> Any:
    if value is None or value == "":
        raise CompileError(code, message, path)
    return value


def _param_default(value: Any) -> Any:
    if isinstance(value, dict) and "default" in value:
        return _param_default(value.get("default"))
    if isinstance(value, dict) and "value" in value:
        return _param_default(value.get("value"))
    return value


def _canonical_id(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_-")
    if not text:
        return "id"
    if not re.match(r"^[a-z0-9]", text):
        return f"id_{text}"
    return text


def _build_canonical_id_map(raw_ids: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for raw_id in raw_ids:
        base = _canonical_id(raw_id)
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        mapping[raw_id] = candidate
        used.add(candidate)
    return mapping


def _normalize_integration_type(raw_type: Any) -> str:
    return INTEGRATION_TYPE_MAP.get(str(raw_type or "custom").lower(), "custom")


def _normalize_io_format(raw_format: Any) -> str | None:
    if raw_format is None:
        return None
    return IO_FORMAT_MAP.get(str(raw_format).lower())


def _normalize_edge_type(raw_edge_type: Any) -> str:
    return EDGE_TYPE_MAP.get(str(raw_edge_type or "success").lower(), "success")


def _normalize_schedule(params: dict[str, Any]) -> dict[str, Any]:
    schedule = params.get("schedule") or {}
    pipeline = params.get("pipeline") or {}

    expression = _param_default(schedule.get("cron"))
    if expression in (None, ""):
        expression = _param_default(schedule.get("expression"))
    schedule_type = str(_param_default(schedule.get("type")) or "").lower()
    catchup = _param_default(schedule.get("catchup"))
    start_date = _param_default(schedule.get("start_date"))
    if start_date in (None, ""):
        start_date = _param_default(pipeline.get("start_date"))

    enabled = False
    cron = None
    if expression not in (None, ""):
        expression_str = str(expression).strip()
        if expression_str.lower() not in {"manual", "none", "null", "on_demand", "ondemand"}:
            enabled = True
            cron = expression_str
    if schedule_type == "cron" and cron:
        enabled = True

    if isinstance(start_date, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", start_date):
        start_date = f"{start_date}T00:00:00Z"

    return _omits_none(
        {
            "enabled": enabled,
            "cron": cron,
            "catchup": catchup,
            "start_date": start_date,
        }
    )


def _topo_components(component_ids: set[str], edges: list[dict[str, str]]) -> list[str]:
    graph: dict[str, list[str]] = {cid: [] for cid in component_ids}
    indeg: dict[str, int] = {cid: 0 for cid in component_ids}

    for edge in edges:
        src = edge["from"]
        dst = edge["to"]
        if src in graph and dst in graph:
            graph[src].append(dst)
            indeg[dst] += 1

    ready = deque(sorted([n for n in component_ids if indeg[n] == 0]))
    out: list[str] = []

    while ready:
        node = ready.popleft()
        out.append(node)
        for nxt in sorted(graph[node]):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)

    if len(out) != len(component_ids):
        return sorted(component_ids)

    return out


def _normalize_parameter(raw: dict[str, Any]) -> dict[str, Any]:
    raw_type = str(raw.get("type", "string")).lower()
    return _omits_none(
        {
            "type": TYPE_MAP.get(raw_type, "STRING"),
            "default": raw.get("default"),
            "description": raw.get("description"),
            "required": bool(raw.get("required", False)),
            "constraints": raw.get("constraints"),
        }
    )


def _collect_secrets(params_env: dict[str, Any], component_id_map: dict[str, str]) -> list[dict[str, Any]]:
    secrets: list[dict[str, Any]] = []
    for name, spec in sorted(params_env.items()):
        entry = {
            "name": name,
            "description": spec.get("description"),
            "required_by_component": component_id_map.get(spec.get("associated_component_id")),
        }
        secrets.append(_omits_none(entry))
    return secrets


def _collect_integration_auth_secrets(
    pipespec: dict[str, Any],
    *,
    component_id_map: dict[str, str],
) -> list[dict[str, Any]]:
    declared = set((pipespec.get("parameters") or {}).get("environment", {}).keys())
    secrets: list[dict[str, Any]] = []
    seen: set[str] = set()

    for connection in pipespec.get("integrations", {}).get("connections", []):
        auth = connection.get("authentication") or {}
        used_by = connection.get("used_by_components") or []
        required_by = component_id_map.get(used_by[0]) if used_by else None
        for key in ("token_env_var", "connection_env_var", "password_secret", "username_secret"):
            secret_name = auth.get(key)
            if (
                isinstance(secret_name, str)
                and secret_name
                and secret_name not in declared
                and secret_name not in seen
            ):
                secrets.append(
                    _omits_none(
                        {
                            "name": secret_name,
                            "description": f"Inferred from integration authentication ({key})",
                            "required_by_component": required_by,
                        }
                    )
                )
                seen.add(secret_name)

    return secrets


def _build_integrations(
    pipespec: dict[str, Any],
    *,
    component_id_map: dict[str, str],
    integration_id_map: dict[str, str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, connection in enumerate(pipespec.get("integrations", {}).get("connections", [])):
        raw_connection_id = _require(
            connection.get("id"),
            "COMP007",
            "integration id is required",
            f"$.integrations.connections[{idx}].id",
        )
        connection_id = integration_id_map[raw_connection_id]

        auth = connection.get("authentication") or {}
        cfg = connection.get("config") or {}

        auth_method = str(auth.get("type", "none")).lower()
        if auth_method == "token":
            method = "token"
        elif auth_method == "connection":
            method = "basic"
        elif auth_method == "unknown":
            method = "none"
        elif auth_method == "password":
            method = "basic"
        elif auth_method == "username_password":
            method = "basic"
        else:
            method = auth_method

        integration = {
            "id": connection_id,
            "name": connection.get("name"),
            "type": _normalize_integration_type(connection.get("type", "custom")),
            "protocol": cfg.get("protocol"),
            "base_url": cfg.get("base_url"),
            "base_path": cfg.get("base_path"),
            "authentication": _omits_none(
                {
                    "method": method,
                    "secret_ref": auth.get("token_env_var") or auth.get("connection_env_var") or auth.get("password_secret"),
                    "username_secret": auth.get("username_secret"),
                    "password_secret": auth.get("password_secret"),
                }
            ),
            "used_by_components": sorted(
                component_id_map.get(component_id, _canonical_id(component_id))
                for component_id in (connection.get("used_by_components") or [])
            ),
            "direction": connection.get("direction"),
            "rate_limit": connection.get("rate_limit"),
        }
        out.append(_omits_none(integration))

    return sorted(out, key=lambda x: x["id"])


def _convert_component(
    comp: dict[str, Any],
    strict: bool,
    comp_idx: int,
    *,
    component_id_map: dict[str, str],
    integration_id_map: dict[str, str],
) -> dict[str, Any]:
    raw_comp_id = _require(comp.get("id"), "COMP002", "component id is required", f"$.components[{comp_idx}].id")
    comp_id = component_id_map[raw_comp_id]
    comp_name = _require(
        comp.get("name"), "COMP003", "component name is required", f"$.components[{comp_idx}].name"
    )
    comp_category = _require(
        comp.get("category"),
        "COMP004",
        "component category is required",
        f"$.components[{comp_idx}].category",
    )

    executor_type_raw = str(comp.get("executor_type", "custom")).lower()
    mapped = EXECUTOR_MAP.get(executor_type_raw)
    if mapped is None:
        if strict:
            raise CompileError(
                "COMP001",
                f"unsupported executor_type: {executor_type_raw}",
                f"$.components[{comp_idx}].executor_type",
            )
        mapped = "custom"

    io_specs = []
    for io_idx, io in enumerate(comp.get("io_spec", [])):
        io_name = _require(
            io.get("name"),
            "COMP005",
            "io name is required",
            f"$.components[{comp_idx}].io_spec[{io_idx}].name",
        )
        io_kind = _require(
            io.get("kind"),
            "COMP006",
            "io kind is required",
            f"$.components[{comp_idx}].io_spec[{io_idx}].kind",
        )
        io_specs.append(
            _omits_none(
                {
                    "name": io_name,
                    "direction": io.get("direction"),
                    "kind": io_kind,
                    "format": _normalize_io_format(io.get("format")),
                    "path_pattern": io.get("path_pattern"),
                    "integration_id": integration_id_map.get(io.get("connection_id")),
                }
            )
        )

    retry = comp.get("retry_policy") or {}
    retry_policy = _omits_none(
        {
            "max_attempts": retry.get("max_attempts", 1),
            "delay_seconds": retry.get("delay_seconds", 30),
            "strategy": "exponential" if retry.get("exponential_backoff") else "constant",
            "multiplier": retry.get("multiplier"),
            "max_delay_seconds": retry.get("max_delay_seconds"),
            "retry_on": retry.get("retry_on"),
        }
    )

    upstream = comp.get("upstream_policy") or {}

    return _omits_none(
        {
            "id": comp_id,
            "name": comp_name,
            "description": comp.get("description"),
            "category": comp_category,
            "executor": {"type": mapped},
            "inputs": [s for s in io_specs if s.get("direction") == "input"],
            "outputs": [s for s in io_specs if s.get("direction") == "output"],
            "parameters": comp.get("executor_config") or {},
            "retry": retry_policy,
            "upstream_policy": upstream.get("type", "all_success"),
            "integrations_used": sorted(
                {
                    integration_id_map[c.get("id")]
                    for c in comp.get("connections", [])
                    if c.get("id") in integration_id_map
                }
            ),
        }
    )


def compile_impl(pipespec: dict[str, Any], options: CompileOptions) -> dict[str, Any]:
    if options.enforce_profile:
        validate_pipespec_profile(pipespec)

    if pipespec.get("pipespec_version") != "1.0":
        raise CompileError("COMP008", "unsupported pipespec_version (expected 1.0)", "$.pipespec_version")

    flow = pipespec.get("flow_structure") or {}
    components = pipespec.get("components") or []
    if not components:
        raise CompileError("COMP009", "pipespec must contain at least one component", "$.components")

    raw_component_ids = [c.get("id") for c in components if c.get("id")]
    component_id_map = _build_canonical_id_map(raw_component_ids)
    raw_integration_ids = [
        connection.get("id")
        for connection in pipespec.get("integrations", {}).get("connections", [])
        if connection.get("id")
    ]
    integration_id_map = _build_canonical_id_map(raw_integration_ids)
    component_ids = set(component_id_map.values())
    edges = [
        _omits_none(
            {
                "from": component_id_map.get(e.get("from"), _canonical_id(e.get("from"))),
                "to": component_id_map.get(e.get("to"), _canonical_id(e.get("to"))),
                "condition": e.get("condition"),
                "edge_type": _normalize_edge_type(e.get("edge_type", "success")),
            }
        )
        for e in flow.get("edges", [])
    ]

    ordered_ids = _topo_components(component_ids, edges)
    by_id = {component_id_map[c["id"]]: c for c in components if c.get("id")}
    index_by_id = {component_id_map[c.get("id")]: idx for idx, c in enumerate(components) if c.get("id")}

    component_out = [
        _convert_component(
            by_id[cid],
            options.strict,
            index_by_id[cid],
            component_id_map=component_id_map,
            integration_id_map=integration_id_map,
        )
        for cid in ordered_ids
        if cid in by_id
    ]

    p_summary = pipespec.get("pipeline_summary") or {}
    p_meta = pipespec.get("metadata") or {}
    params = pipespec.get("parameters") or {}

    pipeline_name = _require(
        p_summary.get("name"),
        "COMP010",
        "pipeline_summary.name is required",
        "$.pipeline_summary.name",
    )
    pipeline_description = _require(
        p_summary.get("description"),
        "COMP011",
        "pipeline_summary.description is required",
        "$.pipeline_summary.description",
    )

    pipeline_params: dict[str, Any] = {}
    for section_name in ("pipeline", "execution", "components"):
        section = params.get(section_name) or {}
        for key, val in section.items():
            if isinstance(val, dict) and "type" in val:
                pipeline_params[key] = _normalize_parameter(val)
            elif isinstance(val, dict):
                for sub_key, sub_val in val.items():
                    pipeline_params[f"{key}.{sub_key}"] = _normalize_parameter(sub_val)

    integrations = _build_integrations(
        pipespec,
        component_id_map=component_id_map,
        integration_id_map=integration_id_map,
    )

    secrets = _collect_secrets(params.get("environment") or {}, component_id_map)
    inferred_secrets = _collect_integration_auth_secrets(
        pipespec,
        component_id_map=component_id_map,
    )

    out = {
        "opos_version": "1.0",
        "pipeline_id": _canonical_id(pipeline_name),
        "description": pipeline_description,
        "metadata": _omits_none(
            {
                "name": pipeline_name,
                "owner": "unknown",
                "domain": "general",
                "complexity": p_summary.get("complexity", "medium"),
                "generator": "llm" if p_meta.get("llm_model") else "template",
                "llm_model": p_meta.get("llm_model"),
                "created": (p_meta.get("analysis_timestamp") or "")[:10] or None,
            }
        ),
        "schedule": _normalize_schedule(params),
        "parameters": pipeline_params,
        "secrets": secrets + inferred_secrets,
        "integrations": integrations,
        "components": component_out,
        "flow": {
            "pattern": flow.get("pattern", "dag"),
            "entry_points": sorted(
                component_id_map.get(entry_point, _canonical_id(entry_point))
                for entry_point in flow.get("entry_points", [])
            ),
            "edges": sorted(edges, key=lambda e: (e.get("from", ""), e.get("to", ""))),
        },
        "provenance": _omits_none(
            {
                "source_file": p_meta.get("source_file"),
                "source_type": "step1_json",
                "generated_at": p_meta.get("analysis_timestamp"),
                "generator_id": p_meta.get("llm_provider"),
                "generator_version": p_meta.get("llm_model"),
                "original_name": pipeline_name,
            }
        ),
    }

    for key in list(out.keys()):
        val = out[key]
        if val in ({}, [], None):
            del out[key]

    return out
