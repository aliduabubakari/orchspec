# Compiler Guide

This guide defines deterministic PipeSpec v1.0 to OrchSpec v1.0 mapping.

## Input Contract (Strict PipeSpec Profile)

Compiler input is validated against:
- `spec/pipespec_profile_v1.json`

If profile validation fails, compiler returns:
- `COMP012` with path-aware message.

## Formal Mapping Spec

Machine-readable mapping policy is stored at:
- `spec/mappings/pipespec_to_orchspec_v1.json`

The compiler reads this spec for:
- executor type mapping
- parameter type mapping
- determinism rules and orchestrator invariants metadata

## Canonical Ordering
- Sort `integrations` by `id`.
- Sort `components` by topological order from `flow.edges`, tie-break with `id`.
- Sort serialized object keys.

## Field Mapping
- `pipeline_summary.name` -> `metadata.name`
- `pipeline_summary.description` -> `description`
- `pipeline_summary.complexity` -> `metadata.complexity`
- `flow_structure.pattern` -> `flow.pattern`
- `flow_structure.entry_points` -> `flow.entry_points`
- `flow_structure.edges` -> `flow.edges`

Executor mapping:
- `python` -> `python_script`
- `http` -> `http_request`
- `sql` -> `sql`
- `bash` -> `bash`
- `container` -> `container`
- `email` -> `email`
- unknown -> `custom` (error in `--strict`)

## Normalization
- Parameter types are normalized to OrchSpec enums (`float` -> `FLOAT`, etc).
- Null/empty values are omitted from output unless required.
- Retry policy maps to OrchSpec `retry` with deterministic defaults.

## Unsupported Input Policy
- Strict mode (`--strict`) raises compile errors with stable IDs.
- Non-strict mode coerces unknown executor types to `custom`.
