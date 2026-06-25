# OrchSpec Specification v1.0

**Orchestration Specification** — a platform-agnostic intermediate representation for pipeline orchestration. OrchSpec is the deterministic compilation target for [PipeSpec](https://github.com/aliduabubakari/pipespec) documents, and the canonical input for multi-orchestrator projection adapters.

---

## Table of Contents

1. [Positioning: PipeSpec → OrchSpec → Orchestrator](#1-positioning-pipespec--orchspec--orchestrator)
2. [Normative Artifacts](#2-normative-artifacts)
3. [Document Model](#3-document-model)
4. [Execution Semantics](#4-execution-semantics)
5. [Validation Model](#5-validation-model)
6. [Determinism Guarantee](#6-determinism-guarantee)
7. [Compilation Contract](#7-compilation-contract)
8. [Projection Model](#8-projection-model)
9. [Schema Extensibility](#9-schema-extensibility)
10. [Versioning & Compatibility](#10-versioning--compatibility)
11. [Security Considerations](#11-security-considerations)

---

## 1. Positioning: PipeSpec → OrchSpec → Orchestrator

OrchSpec sits in the middle of a three-stage pipeline lifecycle:

```
Natural Language / Code Description
        │
        ▼
   [LLM Extraction]
        │
        ▼
   PipeSpec v1.0                          ← Extraction format
   (loose, LLM-friendly,               
    human-oriented)                     
        │
        ▼
   [pipespec2orchspec compiler]           ← Deterministic compilation
        │
        ▼
   OrchSpec v1.0                          ← Canonical IR (this specification)
   (strict, deterministic,
    machine-validated)
        │
        ▼
   [Adapter projection]                   ← Multi-orchestrator emission
        │
        ▼
   Airflow / Prefect / Dagster /          ← Target orchestrator DAGs
   Kestra / Argo / Kubeflow / Flyte
```

### 1.1 What PipeSpec provides

PipeSpec is an LLM-friendly *extraction format* designed for LLMs to describe pipelines from natural language. It is:

- **Flexible**: Allows nulls, optional fields, free-form strings
- **Human-oriented**: Contains prose descriptions alongside structured data
- **Non-deterministic**: Two LLM runs may produce semantically equivalent but structurally different PipeSpec documents
- **Extraction-focused**: Captures "what was understood" from a description, not "what will execute"

PipeSpec is defined in its own repository at [`pipespec`](https://github.com/aliduabubakari/pipespec) with its own JSON Schema (`pipespec_schema_v1.json`).

### 1.2 What OrchSpec adds

OrchSpec is the *canonical intermediate representation* produced by deterministically compiling PipeSpec. It is:

- **Strict**: Every field has a well-defined type, enum, and constraint
- **Deterministic**: Same PipeSpec + same compiler version = byte-identical OrchSpec
- **Machine-validated**: Schema validation + 13 semantic rules (SEM001–SEM013)
- **Projection-ready**: Designed to be consumed by adapter plugins that emit target orchestrator DAGs
- **Diffable**: Semantic diff engine detects breaking vs. non-breaking changes between versions

### 1.3 Why two formats?

| Concern | PipeSpec | OrchSpec |
|---------|----------|----------|
| **Audience** | LLMs, humans reading extraction output | Machines, CI/CD pipelines, orchestrator adapters |
| **Schema strictness** | Loose — nulls allowed, free-form strings | Strict — enums, patterns, required fields |
| **Determinism** | Not guaranteed | Guaranteed (byte-identical output) |
| **Validation depth** | Schema only | Schema + 13 semantic rules + adapter invariants |
| **Purpose** | Describe what the pipeline *is* | Define what the pipeline *will execute* |

---

## 2. Normative Artifacts

The OrchSpec v1.0 specification is defined by the following files. In case of disagreement, the JSON Schema takes precedence over prose descriptions.

| Artifact | Path | Role |
|----------|------|------|
| **JSON Schema** | `spec/orchspec_schema_v1.json` | Normative structural definition. All valid OrchSpec documents MUST validate against this schema. |
| **Compiler Mapping Spec** | `spec/mappings/pipespec_to_orchspec_v1.json` | Machine-readable transformation rules. Defines executor type mapping, parameter type normalization, and determinism rules. |
| **Strict PipeSpec Profile** | `spec/pipespec_profile_v1.json` | Input contract for strict compilation. PipeSpec documents that fail this profile are rejected with `COMP012`. |
| **This document** | `spec/orchspec-spec-v1.md` | Human-readable specification of semantics, validation rules, and guarantees. |
| **Compiler Guide** | `docs/compiler-guide.md` | Field-by-field mapping reference from PipeSpec to OrchSpec. |

---

## 3. Document Model

### 3.1 Top-Level Structure

An OrchSpec document is a JSON object with the following required fields:

| Field | Type | Description |
|-------|------|-------------|
| `orchspec_version` | `string` | MUST be `"1.0"` |
| `pipeline_id` | `string` | Canonical identifier matching `^[a-z0-9][a-z0-9_-]*$`, 1–128 characters |
| `description` | `string` | Human-readable pipeline description, 1–4096 characters |
| `metadata` | `object` | Pipeline identity, ownership, provenance (see §3.2) |
| `components` | `array` | 1+ pipeline components (see §3.3) |
| `flow` | `object` | DAG topology (see §3.4) |

Optional top-level fields:

| Field | Description |
|-------|-------------|
| `schedule` | Cron-based scheduling configuration |
| `parameters` | Typed pipeline parameters with defaults and constraints |
| `variables` | Free-form runtime key-value pairs |
| `secrets` | Secret references with sensitivity levels |
| `integrations` | External system connection catalogue |
| `container_runtime` | Default container image, resources, security context |
| `error_handling` | Failure policies and notification channels |
| `observability` | Logging, metrics, and lineage configuration |
| `ots_export` | Open Transformation Standard export mappings |
| `provenance` | Source file, generator, and timestamp metadata |

### 3.2 Metadata

The `metadata` object captures pipeline identity and provenance:

- `name` (required): Human-readable pipeline name
- `owner` (required): Owning team or individual
- `domain` (required): Business domain (e.g., "finance", "marketing")
- `complexity` (required): One of `low`, `medium`, `high`
- `version`: Semantic version string (`^\d+\.\d+\.\d+$`)
- `tags`: Array of free-form string tags
- `labels`: Free-form key-value metadata (string → string)
- `created` / `updated`: ISO 8601 date strings
- `generator`: One of `reference-manual`, `template`, `llm`, `hybrid`
- `llm_model`: LLM identifier if generated by an LLM
- `case_study`: Reference to source case study or documentation

### 3.3 Components

Each component represents a single pipeline step. Required fields:

- `id`: Unique component identifier matching `^[a-z0-9][a-z0-9_-]*$`
- `name`: Human-readable component name
- `category`: One of `Extractor`, `Transformer`, `Loader`, `Reconciliator`, `QualityCheck`, `Notifier`, `Sensor`, `Custom`
- `executor`: Object with at minimum a `type` field (see §3.3.1)

Optional fields include `description`, `inputs`, `outputs`, `parameters`, `env`, `resources`, `security_context`, `retry`, `timeout`, `upstream_policy`, `script`, `script_language`, `image_override`, and `integrations_used`.

#### 3.3.1 Executor Types

| Type | Description |
|------|-------------|
| `python_script` | Inline or referenced Python code |
| `container` | Docker/OCI container execution |
| `http_request` | HTTP API call |
| `sql` | SQL query or transformation |
| `email` | Email notification |
| `bash` | Shell script execution |
| `custom` | Extension point for unsupported executor types |

#### 3.3.2 Component Categories

| Category | Typical Role | Compatible Executors |
|----------|-------------|---------------------|
| `Extractor` | Ingest data from external sources | python_script, http_request, container, bash, sql, custom |
| `Transformer` | Process, clean, enrich data | python_script, sql, bash, container, custom |
| `Loader` | Write data to destinations | python_script, sql, container, bash, http_request, custom |
| `Reconciliator` | Validate, reconcile, or repair data | python_script, sql, container, custom |
| `QualityCheck` | Data quality gates and assertions | python_script, sql, bash, custom |
| `Notifier` | Send alerts, emails, webhooks | email, http_request, python_script, custom |
| `Sensor` | Wait for external conditions | http_request, python_script, custom |
| `Custom` | Domain-specific pipeline steps | All executor types |

### 3.4 Flow & Topology

The `flow` object defines the pipeline's execution topology:

- `pattern` (required): One of `sequential`, `parallel`, `dag`, `conditional`, `loop`
- `entry_points` (required): Array of component IDs that start execution (≥ 1)
- `edges` (required): Array of directed edges between components

Each edge has:
- `from` / `to`: Source and target component IDs
- `edge_type`: One of `success` (execute on success), `failure` (execute on failure), `always` (execute regardless)
- `condition`: Optional string expression for conditional branching
- `label`: Optional human-readable edge label

Optional `parallelism_groups` define groups of components that can execute concurrently, with an optional `max_concurrent` limit.

---

## 4. Execution Semantics

### 4.1 Flow Patterns

#### 4.1.1 Sequential

Components execute one after another in a strict linear chain. Each component in the chain must have exactly one predecessor and one successor (except the first and last). A sequential flow MUST NOT contain branching nodes (enforced by SEM008).

```
[c1] → [c2] → [c3] → [c4]
```

#### 4.1.2 Parallel

Components execute concurrently where the DAG topology allows. Components with no dependencies on each other MAY execute in parallel. The `parallelism_groups` field can constrain the maximum concurrent executions within a group.

```
         ┌→ [c2] ─┐
[c1] ────┤         ├──→ [c4]
         └→ [c3] ─┘
```

#### 4.1.3 DAG

Directed Acyclic Graph — the general case. Components execute according to their dependencies. Cycles are forbidden (enforced by SEM003). This is the default pattern for most pipelines.

```
[c1] ──→ [c2] ──→ [c4]
   │                ↑
   └──→ [c3] ──────┘
```

#### 4.1.4 Conditional

Components execute based on the evaluation of edge `condition` expressions. An edge with `edge_type: "success"` and a `condition` expression only triggers when the upstream component succeeds AND the condition evaluates to true.

Conditions are strings evaluated by the target orchestrator's expression engine. The specification does not mandate a particular expression language; adapters translate conditions to their target's native syntax (e.g., Jinja for Airflow, Python expressions for Prefect, CEL for Argo).

#### 4.1.5 Loop

Components execute iteratively over a collection. Loop semantics (iteration source, termination, parallelism) are defined by the target adapter. The loop pattern serves as a semantic marker; the actual loop construct is emitted by the adapter.

### 4.2 Upstream Policy

Each component can declare an `upstream_policy` that determines when it triggers:

| Policy | Behavior |
|--------|----------|
| `all_success` | Trigger when ALL upstream components succeed (default) |
| `all_done` | Trigger when ALL upstream components complete, regardless of success/failure |
| `one_success` | Trigger when ANY one upstream component succeeds |
| `none_failed` | Trigger only if NO upstream component has failed |
| `always` | Trigger unconditionally after all upstreams complete |

### 4.3 Error Handling

The top-level `error_handling` section defines pipeline-wide failure behavior:

- `on_failure`: One of `fail_pipeline` (stop all execution), `continue` (let downstream components with `all_done` or `always` policies run), `skip_dependents` (skip only direct dependents)
- `notifications`: Array of notification channels to alert on errors

### 4.4 Retry Behavior

Each component can declare a `retry` policy:

- `max_attempts`: Maximum execution attempts (1–10)
- `strategy`: One of `constant` (fixed delay), `exponential` (multiplying delay), `random` (randomized delay)
- `delay_seconds`: Base delay between retries
- `max_delay_seconds`: Maximum delay cap (for exponential strategy)
- `multiplier`: Growth factor for exponential backoff (must be > 1)
- `retry_on`: Array of error classes that trigger retry

### 4.5 Timeouts

Component timeouts use ISO 8601 duration format with period designator: `PT<value><unit>` where unit is `H` (hours), `M` (minutes), or `S` (seconds). Example: `PT300S` = 5 minutes.

### 4.6 Schedule

When `schedule.enabled` is `true`, a `schedule.cron` expression MUST be present. The schedule model supports:

- `cron`: Standard cron expression
- `timezone`: IANA timezone string
- `start_date` / `end_date`: ISO 8601 datetime boundaries
- `catchup`: Whether to backfill missed intervals
- `max_active_runs`: Maximum concurrent pipeline runs

---

## 5. Validation Model

An OrchSpec document is considered valid if and only if it passes both structural and semantic validation.

### 5.1 JSON Schema Validation

All documents MUST validate against `spec/orchspec_schema_v1.json` (JSON Schema Draft-07). Schema violations produce `SCHEMA_VALIDATION` errors with JSON Pointer paths.

### 5.2 Semantic Validation Rules

Semantic rules validate cross-field and inter-component integrity beyond what JSON Schema can express. Rules SEM001–SEM013 are applied by the `orchspec-validate` tool.

#### Structural Integrity

| Rule | Description | Severity |
|------|-------------|----------|
| SEM001 | `flow.entry_points` must reference existing component IDs | Error |
| SEM002 | `flow.edges` must reference existing component IDs | Error |
| SEM003 | Flow must be acyclic (no cycles in DAG) | Error |
| SEM007 | Component and integration IDs must be unique | Error |
| SEM008 | Sequential flow must not contain branching nodes | Error |
| SEM009 | Schedule requires cron when enabled | Error |

#### Reference Integrity

| Rule | Description | Severity |
|------|-------------|----------|
| SEM004 | `integrations_used` must reference declared integrations | Error |
| SEM005 | IO spec `integration_id` must reference declared integrations | Error |
| SEM006 | Integration authentication secrets must be declared in `secrets` | Error |

#### Category–Executor Compatibility

| Rule | Description | Severity |
|------|-------------|----------|
| SEM010 | Component category must be compatible with executor type | Warning (Error in `--strict`) |

#### Graph Connectivity

| Rule | Description | Severity |
|------|-------------|----------|
| SEM011 | All components must be reachable from entry points | Error |
| SEM012 | Flow graph must be a single weakly connected component (no disconnected subgraphs) | Error |

#### Configuration Coherence

| Rule | Description | Severity |
|------|-------------|----------|
| SEM013 | Retry policy configuration must be internally coherent (multiplier > 1 for exponential, max_delay >= delay) | Error |

#### Resource Integrity

| Rule | Description | Severity |
|------|-------------|----------|
| SEM014 | Resource requests (CPU, memory, GPU) must not exceed limits per component | Error |

#### Security Coherence

| Rule | Description | Severity |
|------|-------------|----------|
| SEM015 | Security context must be internally consistent: `run_as_non_root` cannot have `run_as_user: 0`, dropped capabilities cannot also be added | Error |

#### I/O & Data Flow

| Rule | Description | Severity |
|------|-------------|----------|
| SEM016 | No two components may write to the same output `path_pattern` | Warning |
| SEM017 | Connected components should have compatible I/O kinds (e.g., source outputs `file`, target inputs `table` → warning) | Warning |

#### Condition Expressions

| Rule | Description | Severity |
|------|-------------|----------|
| SEM018 | Edge condition expressions must be non-empty and have balanced parentheses/brackets | Warning |

#### Integration Compatibility

| Rule | Description | Severity |
|------|-------------|----------|
| SEM019 | IO `kind` must be compatible with its associated integration `type` (e.g., `file` → `filesystem` or `object_store`; `table` → `database`) | Warning |

#### Scheduling & Timeouts

| Rule | Description | Severity |
|------|-------------|----------|
| SEM020 | Component timeout must not exceed the schedule interval (component may not complete before next scheduled run) | Warning |

#### Declaration Hygiene

| Rule | Description | Severity |
|------|-------------|----------|
| SEM021 | Parameters and secrets declared at the top level should be consumed by at least one component or integration | Warning |

### 5.3 Strict Mode

With `--strict`, SEM010 warnings are promoted to errors. Non-strict mode treats SEM010 as advisory.

### 5.4 Adapter Invariants

Each orchestrator adapter can declare additional invariants through its `validate_invariants()` method. These are applied after core validation and check for target-specific constraints (e.g., "Airflow does not support SQL executor natively").

---

## 6. Determinism Guarantee

Given identical inputs, the OrchSpec compiler MUST produce byte-identical output. This guarantee enables:

1. **Golden testing**: Regression tests compare compiler output against committed golden files
2. **CI/CD diffing**: Pipeline changes produce deterministic diffs with clear breaking/non-breaking classification
3. **Reproducibility**: Teams can independently verify compilation results

Determinism is achieved through:

### 6.1 Canonical Ordering

- Components are topologically sorted using Kahn's algorithm. Ties are broken by component ID (lexicographic).
- Integrations are sorted by `id`.
- All serialized JSON object keys are sorted lexicographically.
- Edge arrays are sorted by `(from, to)` tuple.

### 6.2 Normalization

- Parameter types are normalized to OrchSpec enums (e.g., `float` → `FLOAT`, `integer` → `INT`)
- IO formats are normalized (e.g., `txt` → `text`)
- Edge types are normalized (e.g., `conditional` → `success` with condition preserved)
- Integration types are normalized (e.g., `objectstore` → `object_store`, `queue` → `message_queue`)
- Schedule expressions are canonicalized (e.g., `"on_demand"` → disabled schedule)

### 6.3 Null/Empty Omission

Fields with `null`, empty string, empty object, or empty array values are omitted from output unless required by the schema.

### 6.4 Canonical IDs

Component and integration IDs are canonicalized from their original PipeSpec forms:
- Lowercased
- Non-alphanumeric characters replaced with underscores
- Leading hyphens/underscores stripped
- Collision resolution via numeric suffix (`_2`, `_3`, ...)

---

## 7. Compilation Contract

### 7.1 Input

The compiler (`pipespec2orchspec`) accepts PipeSpec v1.0 documents that satisfy `pipespec_schema_v1.json`.

### 7.2 Strict PipeSpec Profile

When `--strict` is used, the compiler first validates the input against `spec/pipespec_profile_v1.json` — a stricter profile that rejects:

- Missing required fields at the PipeSpec level
- Unknown executor types
- Invalid flow patterns
- Missing component IDs

Profile violations produce `COMP012` errors with path-aware messages.

### 7.3 Field Mapping

The compiler transforms PipeSpec fields to OrchSpec fields according to the mapping defined in `docs/compiler-guide.md` and the machine-readable `spec/mappings/pipespec_to_orchspec_v1.json`.

Key transformations:

| PipeSpec Field | OrchSpec Field | Notes |
|----------------|----------------|-------|
| `pipeline_summary.name` | `metadata.name` | Also becomes `pipeline_id` |
| `pipeline_summary.description` | `description` | |
| `pipeline_summary.complexity` | `metadata.complexity` | |
| `flow_structure.pattern` | `flow.pattern` | |
| `flow_structure.entry_points` | `flow.entry_points` | IDs canonicalized |
| `flow_structure.edges` | `flow.edges` | Edge types normalized |
| `components[].executor_type` | `components[].executor.type` | Mapped via executor table |
| `components[].io_spec` | `components[].inputs` + `components[].outputs` | Split by direction |
| `parameters.*` | `parameters` | Types normalized to uppercase enums |
| `integrations.connections` | `integrations` | IDs canonicalized, types normalized |

### 7.4 Error Codes

| Code | Description |
|------|-------------|
| COMP001 | Unsupported executor type (strict mode) |
| COMP002 | Component ID required |
| COMP003 | Component name required |
| COMP004 | Component category required |
| COMP005 | IO spec name required |
| COMP006 | IO spec kind required |
| COMP007 | Integration ID required |
| COMP008 | Unsupported pipespec_version (must be 1.0) |
| COMP009 | PipeSpec must contain at least one component |
| COMP010 | pipeline_summary.name is required |
| COMP011 | pipeline_summary.description is required |
| COMP012 | PipeSpec profile validation failed |

---

## 8. Projection Model

### 8.1 Adapter Protocol

OrchSpec documents are projected onto target orchestrators through pluggable adapters. Every adapter implements the `OrchspecAdapter` Protocol:

```python
class OrchspecAdapter(Protocol):
    def capability(self) -> AdapterCapability: ...
    def validate_invariants(self, orchspec_doc: dict) -> list[str]: ...
    def project(self, orchspec_doc: dict) -> ProjectionResult: ...
```

### 8.2 Capability Declaration

Each adapter declares its capabilities:
- `target`: Target orchestrator name (e.g., "airflow", "prefect")
- `runtime_style`: `imperative` or `declarative`
- `supported_executors`: List of executor types the target natively supports

### 8.3 Invariant Validation

Before projection, adapters validate target-specific constraints. Examples:
- "Airflow does not natively support SQL executor — wrap in container"
- "Kestra requires all tasks to have a unique flow identifier"
- "Argo cannot express `all_done` upstream policy"

Violations prevent projection and are returned as human-readable messages.

### 8.4 Projection

The `project()` method transforms an OrchSpec document into a target-specific intermediate representation. In v1.0, adapters emit stub IR. Future versions will emit full target-native definitions (Airflow DAG Python, Prefect Flow, Kestra YAML flow, Argo WorkflowTemplate, etc.).

### 8.5 Built-in Adapters

| Adapter | Target | Style |
|---------|--------|-------|
| AirflowAdapter | Apache Airflow 2.x | imperative |
| PrefectAdapter | Prefect 2.x/3.x | imperative |
| DagsterAdapter | Dagster | imperative |
| KestraAdapter | Kestra | declarative |
| ArgoAdapter | Argo Workflows | declarative |
| KubeflowAdapter | Kubeflow Pipelines | declarative |
| FlyteAdapter | Flyte | declarative |

---

## 9. Schema Extensibility

OrchSpec is designed for extension at multiple layers without requiring changes to the core specification.

### 9.1 Extension Points

| Mechanism | Use Case | Example |
|-----------|----------|---------|
| `executor.type: "custom"` | Non-standard execution engines | Kafka connector, gRPC service |
| `category: "Custom"` | Domain-specific component types | ML training, feature engineering |
| `integration.type: "custom"` | Unlisted external systems | Redis cache, Elasticsearch |
| `metadata.labels` | Arbitrary key-value metadata | cost_center, compliance tags |
| `metadata.tags` | Free-form taxonomy | ["finance", "critical", "pii"] |
| JSON Schema `allOf` wrappers | Domain-specific required fields | GDPR fields, SOC2 audit fields |
| `ots_export` | Transformation layer mapping | dbt models, SQLMesh projections |
| Adapter plugins | New orchestrator targets | Temporal, Metaflow, Dagster+ |

### 9.2 Wrapper Schemas

Organizations that need domain-specific fields can create wrapper schemas that extend the canonical schema via `allOf`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "allOf": [
    { "$ref": "orchspec_schema_v1.json" },
    {
      "properties": {
        "compliance": {
          "type": "object",
          "properties": {
            "gdpr_scope": { "type": "boolean" },
            "data_retention_days": { "type": "integer" }
          }
        }
      }
    }
  ]
}
```

This keeps the core schema clean and independently versioned while allowing domain-specific validation.

### 9.3 Custom Adapters

New orchestrator adapters follow a standard pattern:

1. Create a class implementing `OrchspecAdapter` Protocol
2. Override `validate_invariants()` for target-specific checks
3. Override `project()` to emit target-native IR
4. Register in the adapter registry

Adapters are autonomously testable — given an OrchSpec document, verify the adapter emits structurally valid target IR without requiring the actual orchestrator runtime.

---

## 10. Versioning & Compatibility

### 10.1 Schema Versioning

OrchSpec follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version bump: Breaking changes to the schema (fields removed, types changed, validation rules tightened to errors)
- **MINOR** version bump: New optional fields, new semantic rules that are warnings by default, new adapter targets
- **PATCH** version bump: Documentation fixes, compiler bug fixes that don't change output, test improvements

### 10.2 Backward Compatibility

Within a MAJOR version:
- Documents valid under version `v1.N` MUST remain valid under `v1.N+1`
- New fields added in `v1.N+1` MUST be optional
- New semantic rules in `v1.N+1` MUST be warnings by default (promotable to errors under `--strict`)

### 10.3 Compiler Version Pinning

The compiler version is embedded in the output's `provenance.generator_version` field. Consumers SHOULD pin to a specific compiler version for reproducibility.

---

## 11. Security Considerations

### 11.1 Secret Handling

OrchSpec documents contain secret *references*, never secret *values*. Secrets are identified by:
- `secrets[].name`: Logical secret name
- `secrets[].sensitivity`: Classification level (`low`, `medium`, `high`, `critical`)
- `secrets[].env_var_fallback`: Environment variable name for runtime injection
- Integration `authentication.secret_ref`: Reference to a declared secret

OrchSpec documents MUST NOT contain actual credentials, API keys, tokens, or passwords.

### 11.2 Container Security

The `container_runtime.security_context` and per-component `security_context` fields define:
- `run_as_non_root`: Whether to enforce non-root execution
- `read_only_root_filesystem`: Whether the root filesystem is read-only
- `drop_capabilities` / `add_capabilities`: Linux capability management
- `run_as_user` / `run_as_group`: UID/GID constraints

Adapters SHOULD respect these security contexts when generating target orchestrator definitions.

### 11.3 Authentication

Integration authentication declares the method (`none`, `api_key`, `basic`, `bearer`, `oauth2`, `token`) and references secrets by name. Actual credentials are resolved at runtime by the target orchestrator's secret backend.

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **PipeSpec** | LLM-friendly pipeline extraction format; input to the OrchSpec compiler |
| **OrchSpec** | Canonical intermediate representation for pipeline orchestration |
| **IR** | Intermediate Representation |
| **DAG** | Directed Acyclic Graph |
| **Adapter** | Pluggable module that projects OrchSpec onto a specific orchestrator |
| **Projection** | The act of transforming an OrchSpec document into target-specific IR |
| **Deterministic** | Same input + same compiler version = byte-identical output |
| **Canonical** | The authoritative, normalized form of a document |
| **SEM001–SEM013** | Semantic validation rules enforced by `orchspec-validate` |
| **COMP001–COMP012** | Compiler error codes emitted by `pipespec2orchspec` |

## Appendix B: Conformance

An implementation conforms to OrchSpec v1.0 if:

1. It accepts and produces documents that validate against `orchspec_schema_v1.json`
2. It enforces SEM001–SEM013 as specified in §5
3. It produces deterministic output as specified in §6
4. It implements the adapter protocol as specified in §8

An implementation MAY extend the specification through the mechanisms described in §9. Extensions that do not violate the base schema remain conformant.
