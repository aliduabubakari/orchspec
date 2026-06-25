# OrchSpec v1 — LLM Skills Reference

> **A self-contained guide for any LLM to generate valid OrchSpec (OrchSpec) v1 canonical pipeline documents.**
>
> OrchSpec (the Orchestrator-Agnostic Canonical Specification) is a universal pipeline abstraction layer.
> PipeSpec documents are deterministically compiled into OrchSpec, which can then be projected into
> orchestrator-specific formats (Airflow, Prefect, Dagster, Kestra, Argo, KFP, Flyte).
>
> Use this reference to understand OrchSpec structure, produce valid `.orchspec.yaml` / `.orchspec.json` documents,
> and reason about pipeline semantics at the canonical layer.

---

## 1. What OrchSpec Is

OrchSpec captures the **canonical, orchestrator-agnostic skeleton** of a data pipeline:

- **What** each component does (category, executor type, I/O, retry policy)
- **How** components connect (DAG topology: pattern + entry points + edges)
- **What** external systems they touch (integrations catalogue)
- **What** secrets and parameters they need (typed parameters + secret references)
- **How** the pipeline is scheduled, containerized, observed, and error-handled

OrchSpec does **NOT** embed full business logic payloads — it captures the component boundary, not the implementation.

### Relationship to PipeSpec

PipeSpec is the *intent* layer (what the user describes). OrchSpec is the *canonical* layer (what the compiler produces).
Key differences:

| Aspect | PipeSpec | OrchSpec |
|--------|----------|----------|
| Identity | `pipespec_version: "1.0"` | `orchspec_version: "1.0"` |
| Pipeline name | `pipeline_summary.name` | `pipeline_id` (snake_case) + `metadata.name` |
| Executor types | `python`, `http`, `docker` | `python_script`, `http_request`, `container` |
| Parameter types | lowercase (`string`, `int`) | UPPERCASE (`STRING`, `INT`) |
| Flow nodes | explicit `flow_structure.nodes` map | implicit — components *are* the nodes |
| I/O spec | `io_spec[]` with `direction` field | separate `inputs[]` and `outputs[]` arrays |
| Integrations | `integrations.connections[]` | `integrations[]` (flat array) |

---

## 2. Top-Level Document Structure

A valid OrchSpec v1 document is a single JSON or YAML object with **6 required keys**:

| Key | Type | Description |
|-----|------|-------------|
| `orchspec_version` | `string` | Must be `"1.0"` |
| `pipeline_id` | `string` | Unique pipeline identifier (snake_case, `^[a-z0-9][a-z0-9_-]*$`) |
| `description` | `string` | Human-readable pipeline overview (1–4096 chars) |
| `metadata` | `object` | Provenance, ownership, domain, complexity |
| `components` | `array` | List of pipeline components (min 1 item) |
| `flow` | `object` | Directed graph topology (pattern + entry_points + edges) |

Optional keys:

| Key | Type | Description |
|-----|------|-------------|
| `schedule` | `object` | Cron schedule and runtime window |
| `parameters` | `object` | Typed pipeline parameters (map of name → Parameter) |
| `variables` | `object` | Arbitrary key-value variables (additionalProperties: true) |
| `secrets` | `array` | Secret references (name, sensitivity, component associations) |
| `integrations` | `array` | External system catalogue |
| `container_runtime` | `object` | Container image, resource defaults, volumes, security |
| `error_handling` | `object` | Failure policy and notification channels |
| `observability` | `object` | Logging, metrics, and lineage configuration |
| `ots_export` | `object` | Optional OTS (Ontology Transformation Service) export config |
| `provenance` | `object` | Source file, generator info, generation timestamp |

---

## 3. Identifier Convention

All component, integration, secret, and pipeline IDs must match: `^[a-z0-9][a-z0-9_-]*$` (1–128 chars, starts with lowercase alphanumeric).

**OrchSpec uses lowercase snake_case for IDs.** This differs from PipeSpec which allows PascalCase.

Examples: `extract_api`, `validate_json`, `load_to_postgres`, `airvisual_api`, `local_filesystem`

---

## 4. `metadata` — Provenance & Ownership

```jsonc
{
  "name": "My Pipeline",                  // REQUIRED. string
  "owner": "data-engineering",            // REQUIRED. string
  "domain": "marketing",                  // REQUIRED. string
  "complexity": "medium",                 // REQUIRED. "low" | "medium" | "high"
  "version": "1.0.0",                    // optional. semver pattern ^\d+\.\d+\.\d+$
  "tags": ["etl", "daily"],               // optional. string[]
  "labels": { "env": "prod" },            // optional. string→string map
  "created": "2026-01-15",               // optional. date string
  "updated": "2026-05-01",               // optional. date string
  "generator": "llm",                     // optional. "reference-manual" | "template" | "llm" | "hybrid"
  "llm_model": "gpt-4o",                 // optional. string
  "case_study": "marketing-attribution"   // optional. string
}
```

All four required fields (`name`, `owner`, `domain`, `complexity`) must be present.

### Complexity (enum)

| Value | When to use |
|-------|------------|
| `low` | ≤3 components, sequential, no branching |
| `medium` | 4–10 components, some branching/parallelism |
| `high` | >10 components, complex DAG, many integrations |

---

## 5. `components[]` — The Task Catalogue

Each component describes one unit of work:

```jsonc
{
  "id": "extract_api",                        // REQUIRED. lowercase snake_case Id
  "name": "Extract API Data",                  // REQUIRED. human-readable string
  "category": "Extractor",                     // REQUIRED. ComponentCategory enum (PascalCase)
  "description": "Fetches data from REST API", // optional string
  "executor": {                                // REQUIRED. Executor object
    "type": "python_script"                    //   REQUIRED. ExecutorType enum (snake_case)
  },

  // OPTIONAL structured I/O:
  "inputs": [
    {
      "name": "source_data",                  // REQUIRED. string
      "kind": "file",                         // REQUIRED. "file" | "table" | "api" | "object" | "stream" | "secret" | "volume"
      "format": "csv",                        // optional. "json" | "csv" | "parquet" | "avro" | "html" | "sql" | "text" | "binary"
      "direction": "input",                   // optional. "input" | "output"
      "path_pattern": "/data/input.csv",      // optional. string or omitted
      "integration_id": "local_fs",           // optional. must match integrations[].id
      "schema_ref": null,                     // optional. string or omitted
      "optional": false                       // optional. boolean
    }
  ],
  "outputs": [
    {
      "name": "api_response",
      "kind": "object",
      "format": "json",
      "direction": "output"
    }
  ],

  // OPTIONAL component configuration:
  "parameters": { "batch_size": 1000 },        // optional. arbitrary key-value
  "env": { "LOG_LEVEL": "INFO" },              // optional. string→string map
  "resources": {                               // optional. CPU/Memory/GPU specs
    "request": { "cpu": "0.5", "memory": "512Mi" },
    "limit": { "cpu": "1", "memory": "1Gi" }
  },
  "security_context": {                        // optional
    "run_as_non_root": true,
    "run_as_user": 1000
  },
  "retry": {                                   // optional. RetryPolicy
    "max_attempts": 3,                         //   REQUIRED if retry present. 1–10
    "strategy": "exponential",                 //   optional. "constant" | "exponential" | "random"
    "delay_seconds": 60,                       //   optional. integer ≥ 0
    "max_delay_seconds": 600,                  //   optional. integer
    "multiplier": 2.0,                         //   optional. ≥ 1.0
    "retry_on": ["timeout", "network_error"]   //   optional. string[]
  },
  "timeout": "PT1H",                           // optional. ISO 8601 duration pattern PT\d+(H|M|S)
  "upstream_policy": "all_success",            // optional. "all_success" | "all_done" | "one_success" | "none_failed" | "always"
  "script": "SELECT * FROM users",             // optional. inline script body
  "script_language": "sql",                    // optional. "python" | "bash" | "sql" | "r"
  "image_override": "python:3.11-slim",        // optional. container image override
  "integrations_used": ["postgres_warehouse"]  // optional. string[] referencing integrations[].id
}
```

### Component Categories (enum — 8 values, PascalCase)

| Category | When to use |
|----------|------------|
| `Extractor` | Fetches/reads data from an external source |
| `Transformer` | Transforms, enriches, or reshapes data |
| `Loader` | Writes/loads data into a target system |
| `Reconciliator` | Compares or reconciles datasets |
| `QualityCheck` | Validates data quality |
| `Notifier` | Sends notifications (email, Slack, webhook) — no data transformation |
| `Sensor` | Waits for an external condition or event |
| `Custom` | Anything that doesn't map cleanly to the above |

⚠️ Categories use **PascalCase** (capitalized), matching PipeSpec convention for this field.

### Executor Types (enum — 7 values, snake_case)

| Type | Description | PipeSpec equivalent |
|------|-------------|---------------------|
| `python_script` | Python script or callable | `python` |
| `container` | Container-based execution | `docker` / `container` |
| `http_request` | HTTP request/callout | `http` |
| `sql` | SQL execution | `sql` |
| `email` | Email sending | `email` |
| `bash` | Shell script or command | `bash` |
| `custom` | Anything else | `custom` |

⚠️ Executor types use **snake_case** — this differs from PipeSpec. The compiler maps `python` → `python_script`, `http` → `http_request`, `docker` → `container`.

### Executor Object — Additional Properties

Beyond `type`, the executor object can include optional target-specific fields:

| Field | Type | When to use |
|-------|------|-------------|
| `image` | `string` | Container image name (for container executor) |
| `python_callable` | `string` | Fully qualified python function (for python_script) |
| `http_method` | `string` | `GET` / `POST` / `PUT` / `DELETE` / `PATCH` (for http_request) |
| `sql_connection_id` | `string` | Integration ID for DB connection (for sql) |
| `custom_class` | `string` | Custom executor class reference (for custom) |

### Category/Executor Compatibility

Not all combinations make sense. The semantic validator (SEM010) checks:

| Category | Allowed executor types |
|----------|----------------------|
| `Extractor` | `python_script`, `http_request`, `container`, `bash`, `sql`, `custom` |
| `Transformer` | `python_script`, `sql`, `bash`, `container`, `custom` |
| `Loader` | `python_script`, `sql`, `container`, `bash`, `http_request`, `custom` |
| `QualityCheck` | `python_script`, `sql`, `bash`, `custom` |
| `Notifier` | `email`, `http_request`, `python_script`, `custom` |
| `Sensor` | `http_request`, `python_script`, `custom` |
| `Reconciliator` | `python_script`, `sql`, `container`, `custom` |
| `Custom` | `custom`, `python_script`, `container`, `bash`, `sql`, `http_request`, `email` |

### I/O Spec — `inputs[]` and `outputs[]`

Each I/O item requires: `name`, `kind`. The `direction` field is optional (the array name implies direction, unlike PipeSpec's combined `io_spec[]`).

| Kind | Meaning |
|------|---------|
| `file` | File on a filesystem |
| `table` | Database table or view |
| `api` | REST/GraphQL API endpoint |
| `object` | In-memory object (dataframe, dict) |
| `stream` | Streaming data (Kafka, Kinesis) |
| `secret` | Secret/credential reference |
| `volume` | Container volume mount |

| Format | Typical file extension / meaning |
|--------|----------------------------------|
| `json` | JSON data |
| `csv` | Comma-separated values |
| `parquet` | Apache Parquet |
| `avro` | Apache Avro |
| `html` | HTML content |
| `sql` | SQL query/result |
| `text` | Plain text |
| `binary` | Binary blob |

### Retry Policy

If present, `max_attempts` is required (1–10). Other fields are optional.

| Strategy | Behavior |
|----------|----------|
| `constant` | Fixed delay between retries |
| `exponential` | Delay grows exponentially (uses `multiplier`, requires `multiplier` > 1 per SEM013) |
| `random` | Random delay within bounds |

SEM013 enforces: `max_delay_seconds` ≥ `delay_seconds` when both are set, and `multiplier` > 1 for exponential strategy.

---

## 6. `flow` — Pipeline Topology

```jsonc
{
  "pattern": "dag",                                    // REQUIRED. FlowPattern enum
  "entry_points": ["extract_api", "extract_db"],        // REQUIRED. string[], min 1
  "edges": [                                            // REQUIRED. Edge[]
    {
      "from": "extract_api",                            // REQUIRED. component id
      "to": "transform_data",                           // REQUIRED. component id
      "edge_type": "success",                           // optional. "success" | "failure" | "always"
      "condition": null,                                // optional. string (for conditional edges)
      "label": "API → Transform"                        // optional. human-readable label
    }
  ],
  "parallelism_groups": [                               // optional
    {
      "id": "parallel_transform_group",                 // REQUIRED. string
      "component_ids": ["transform_a", "transform_b"],   // REQUIRED. string[]
      "max_concurrent": 4                                // optional. int ≥ 1
    }
  ]
}
```

### Flow Patterns (enum)

| Value | Meaning |
|-------|---------|
| `sequential` | Tasks run one after another (fan-out ≤ 1, enforced by SEM008) |
| `parallel` | Tasks run concurrently |
| `dag` | General directed acyclic graph |
| `conditional` | Branching with conditions |
| `loop` | Intentional cycles allowed (no SEM003 cycle check) |

### Critical Rules for Flow

1. **Components ARE the nodes.** Unlike PipeSpec, OrchSpec has no separate `flow_structure.nodes` map. The `components[]` list defines the node set. Edge `from`/`to` values must be valid component `id` values.
2. **entry_points** reference component IDs that start the pipeline execution.
3. **DAG acyclicity** is enforced (SEM003) for `sequential`, `parallel`, and `dag` patterns.
4. **All components must be reachable** from entry points (SEM011).
5. **Flow must be a single connected component** — no disconnected subgraphs (SEM012).
6. **Sequential flow** cannot branch (fan-out > 1 triggers SEM008).
7. **Edges** are ordered canonically by `(from, to)` for deterministic serialization.

### Edge Types

| Type | Meaning |
|------|---------|
| `success` | Follow when upstream succeeds (default if omitted) |
| `failure` | Follow when upstream fails |
| `always` | Always follow regardless of outcome |

### Parallelism Groups

Optional grouping of components for parallel execution control.

---

## 7. `integrations[]` — External System Catalogue

```jsonc
{
  "id": "postgres_warehouse",                  // REQUIRED. lowercase Id
  "name": "PostgreSQL Warehouse",              // optional. human-readable string
  "type": "database",                          // REQUIRED. IntegrationType enum
  "protocol": "postgresql",                    // optional. string
  "base_url": null,                            // optional. string (for api type)
  "host": "db.example.com",                    // optional. string
  "port": 5432,                                // optional. integer
  "database": "analytics",                     // optional. string
  "base_path": "/data",                        // optional. string (for filesystem type)
  "authentication": {                          // optional, but method is required if present
    "method": "basic",                         //   REQUIRED if auth present. "none" | "api_key" | "basic" | "bearer" | "oauth2" | "token"
    "secret_ref": "db_password",               //   optional. references secrets[].name
    "username_secret": "db_user",              //   optional. references secrets[].name
    "password_secret": "db_password"           //   optional. references secrets[].name
  },
  "used_by_components": ["load_to_db"],         // optional. string[]
  "direction": "output",                        // optional. "input" | "output" | "both"
  "rate_limit": "100/minute"                    // optional. pattern ^\d+/(second|minute|hour|day)$
}
```

### Integration Types (enum)

| Type | Typical use |
|------|------------|
| `api` | REST/GraphQL API endpoints |
| `database` | Relational databases |
| `filesystem` | Local/network filesystem paths |
| `object_store` | S3, GCS, Azure Blob |
| `message_queue` | Kafka, RabbitMQ, SQS |
| `smtp` | Email (SMTP) |
| `custom` | Anything else |

### Integration Direction

| Value | Meaning |
|-------|---------|
| `input` | Pipeline only reads from this system |
| `output` | Pipeline only writes to this system |
| `both` | Pipeline reads and writes |

### Authentication Methods

| Method | When to use |
|--------|------------|
| `none` | No authentication required |
| `api_key` | API key in header/query param |
| `basic` | Username + password |
| `bearer` | Bearer token |
| `oauth2` | OAuth 2.0 flow |
| `token` | Static token |

⚠️ **SECRET HYGIENE**: Authentication objects reference secrets by name (`secret_ref`, `username_secret`, `password_secret`). These must resolve to `secrets[].name` values (SEM006). Never embed actual credentials.

---

## 8. `secrets[]` — Secret References

```jsonc
{
  "name": "db_password",                        // REQUIRED. string
  "description": "Database password",           // optional. string
  "required_by_component": "load_to_db",        // optional. component id
  "env_var_fallback": "DB_PASSWORD",            // optional. environment variable name
  "sensitivity": "critical"                     // optional. "low" | "medium" | "high" | "critical"
}
```

### ⚠️ SECRET HYGIENE — CRITICAL

- **NEVER embed actual secret values** in an OrchSpec document.
- Secrets reference the secret **name** only. The actual value is resolved at runtime from the orchestrator's secret store.
- `sensitivity` helps orchestrators apply appropriate access controls.
- `env_var_fallback` provides the environment variable name for local/dev execution.

---

## 9. `parameters` — Typed Pipeline Parameters

```jsonc
{
  "batch_size": {
    "type": "INT",                              // REQUIRED. ParamType enum (UPPERCASE)
    "default": 1000,                            // optional. any JSON value
    "description": "Records per batch",         // optional. string
    "required": false,                          // optional. boolean
    "constraints": "Must be > 0"                // optional. human-readable constraint
  }
}
```

### Parameter Types (enum — UPPERCASE)

| Type | PipeSpec equivalent |
|------|---------------------|
| `STRING` | `string` |
| `INT` | `integer` / `int` |
| `FLOAT` | `float` |
| `BOOLEAN` | `boolean` |
| `DATETIME` | `datetime` |
| `DATE` | `date` |
| `FILE` | `file` |
| `JSON` | `json` |
| `ARRAY` | `array` |

⚠️ Parameter types are **UPPERCASE** in OrchSpec, unlike PipeSpec's lowercase types. The compiler normalizes: `string` → `STRING`, `int` → `INT`, etc.

---

## 10. `schedule` — Cron Scheduling

```jsonc
{
  "enabled": true,                              // optional. boolean
  "cron": "0 6 * * *",                          // optional, but REQUIRED if enabled = true (SEM009)
  "timezone": "America/New_York",               // optional. string
  "start_date": "2026-01-01T00:00:00Z",         // optional. ISO 8601 date-time
  "end_date": "2026-12-31T23:59:59Z",           // optional. ISO 8601 date-time
  "catchup": false,                             // optional. boolean
  "max_active_runs": 3                           // optional. integer ≥ 1
}
```

⚠️ SEM009 enforces: if `enabled` is `true`, `cron` must be present.

---

## 11. `container_runtime` — Container Configuration

```jsonc
{
  "default_image": "python:3.11-slim",          // optional. string
  "image_pull_policy": "IfNotPresent",          // optional. "Always" | "IfNotPresent" | "Never"
  "resource_defaults": {                        // optional
    "request": { "cpu": "0.5", "memory": "512Mi" },
    "limit": { "cpu": "1", "memory": "1Gi" }
  },
  "security_context": {                         // optional
    "run_as_non_root": true,
    "run_as_user": 1000,
    "run_as_group": 1000,
    "allow_privilege_escalation": false,
    "read_only_root_filesystem": true,
    "drop_capabilities": ["ALL"],
    "add_capabilities": []
  },
  "working_dir": "/app",                        // optional. string
  "volumes": [                                  // optional
    {
      "name": "data-volume",                    //   REQUIRED. string
      "mount_path": "/data",                    //   optional. string
      "size": "10Gi",                           //   optional. string
      "access_mode": "ReadWriteOnce",           //   optional. "ReadWriteOnce" | "ReadOnlyMany" | "ReadWriteMany"
      "read_only": false                        //   optional. boolean
    }
  ]
}
```

### ResourceSpec

Used for both `request` and `limit`:

| Field | Type | Example |
|-------|------|---------|
| `cpu` | `string` | `"0.5"`, `"1"`, `"2"` |
| `memory` | `string` | `"512Mi"`, `"1Gi"`, `"4Gi"` |
| `gpu` | `integer` ≥ 0 | `0`, `1`, `4` |

---

## 12. `error_handling` — Failure Behavior & Notifications

```jsonc
{
  "on_failure": "fail_pipeline",                // optional. "fail_pipeline" | "continue" | "skip_dependents"
  "notifications": [                            // optional
    {
      "channel": "slack",                       //   "log" | "email" | "slack" | "webhook" | "pagerduty"
      "level": "ERROR",                         //   "INFO" | "WARN" | "ERROR" | "CRITICAL"
      "message": "Pipeline failed!",
      "recipients": ["#data-alerts"],           //   string[] (optional)
      "webhook_url": null                       //   string (optional, required for webhook channel)
    }
  ]
}
```

---

## 13. `observability` — Logging, Metrics, Lineage

```jsonc
{
  "logging": {
    "level": "INFO",                            // "DEBUG" | "INFO" | "WARNING" | "ERROR"
    "format": "json"                            // "json" | "text"
  },
  "metrics": {
    "enabled": true,
    "standard": [                               // subset of:
      "pipeline_duration",                      //   pipeline total duration
      "component_duration",                     //   per-component duration
      "component_success_rate",                 //   per-component success rate
      "rows_processed",                         //   rows processed
      "bytes_processed"                         //   bytes processed
    ]
  },
  "lineage": {
    "enabled": true,
    "format": "openlineage",                    // "openlineage" | "datahub" | "custom"
    "export_endpoint": "https://lineage.example.com"
  }
}
```

---

## 14. Additional Optional Sections

### `ots_export` — OTS (Ontology Transformation Service) Export Config

```jsonc
{
  "ots_version": "2.0",
  "module_id": "analytics_pipeline",
  "component_mappings": [
    {
      "component_id": "transform_data",         // REQUIRED. references components[].id
      "ots_type": "sql_transformation",         // REQUIRED. "sql_transformation" | "python_model" | "external_source" | "external_sink"
      "ots_transformation_id": "tr_001",
      "materialization": "table"                // "table" | "view" | "incremental" | "ephemeral"
    }
  ]
}
```

### `provenance` — Generation Provenance

```jsonc
{
  "source_file": "pipeline_description.txt",   // optional. string
  "source_type": "step1_json",                  // optional. "step1_json" | "manual" | "migrated" | "template"
  "source_version": "1.0",                     // optional. string
  "generated_at": "2026-05-29T12:00:00Z",       // optional. ISO 8601 date-time
  "generator_id": "pipespec2orchspec",             // optional. string
  "generator_version": "1.0.0",                // optional. string
  "original_name": "My ETL Pipeline"            // optional. string
}
```

### `variables`

An arbitrary key-value store with no schema constraints (`additionalProperties: true`):

```jsonc
{
  "environment": "production",
  "cost_center": "eng-1234"
}
```

---

## 15. Complete Minimal Example

Below is the smallest valid OrchSpec v1 document (YAML format, `.orchspec.yaml`):

```yaml
orchspec_version: '1.0'
pipeline_id: simple_etl
description: Extract CSV, transform, load to PostgreSQL
metadata:
  name: Simple ETL Pipeline
  owner: data-engineering
  domain: general
  complexity: low
  generator: reference-manual
components:
  - id: extract_csv
    name: Extract CSV Data
    category: Extractor
    executor:
      type: python_script
    inputs:
      - name: source_csv
        kind: file
        format: csv
        integration_id: local_fs
    outputs:
      - name: raw_data
        kind: object
        format: json
    retry:
      max_attempts: 1
    upstream_policy: all_success
  - id: transform_data
    name: Transform Data
    category: Transformer
    executor:
      type: python_script
    inputs:
      - name: raw_data
        kind: object
    outputs:
      - name: clean_data
        kind: object
    retry:
      max_attempts: 2
      strategy: constant
      delay_seconds: 30
    upstream_policy: all_success
  - id: load_to_db
    name: Load to PostgreSQL
    category: Loader
    executor:
      type: sql
      sql_connection_id: pg_warehouse
    inputs:
      - name: clean_data
        kind: object
    outputs:
      - name: target_table
        kind: table
        format: sql
        integration_id: pg_warehouse
    retry:
      max_attempts: 3
      strategy: exponential
      delay_seconds: 60
      max_delay_seconds: 600
      multiplier: 2.0
    upstream_policy: all_success
    integrations_used:
      - pg_warehouse
flow:
  pattern: sequential
  entry_points:
    - extract_csv
  edges:
    - from: extract_csv
      to: transform_data
      edge_type: success
    - from: transform_data
      to: load_to_db
      edge_type: success
integrations:
  - id: local_fs
    name: Local Filesystem
    type: filesystem
    authentication:
      method: none
    direction: input
  - id: pg_warehouse
    name: PostgreSQL Warehouse
    type: database
    protocol: postgresql
    host: db.example.com
    port: 5432
    database: analytics
    authentication:
      method: basic
      username_secret: db_user
      password_secret: db_password
    direction: output
secrets:
  - name: db_user
    description: Database username
    sensitivity: medium
  - name: db_password
    description: Database password
    sensitivity: critical
    env_var_fallback: DB_PASSWORD
schedule:
  enabled: true
  cron: '0 6 * * *'
  timezone: UTC
```

Equivalent minimal JSON form:

```json
{
  "orchspec_version": "1.0",
  "pipeline_id": "simple_etl",
  "description": "Extract CSV, transform, load to PostgreSQL",
  "metadata": {
    "name": "Simple ETL Pipeline",
    "owner": "data-engineering",
    "domain": "general",
    "complexity": "low"
  },
  "components": [
    {
      "id": "extract_csv",
      "name": "Extract CSV Data",
      "category": "Extractor",
      "executor": { "type": "python_script" },
      "retry": { "max_attempts": 1 }
    },
    {
      "id": "transform_data",
      "name": "Transform Data",
      "category": "Transformer",
      "executor": { "type": "python_script" },
      "retry": { "max_attempts": 1 }
    },
    {
      "id": "load_to_db",
      "name": "Load to PostgreSQL",
      "category": "Loader",
      "executor": { "type": "sql" },
      "retry": { "max_attempts": 1 }
    }
  ],
  "flow": {
    "pattern": "sequential",
    "entry_points": ["extract_csv"],
    "edges": [
      { "from": "extract_csv", "to": "transform_data" },
      { "from": "transform_data", "to": "load_to_db" }
    ]
  }
}
```

---

## 16. Generation Checklist

When generating an OrchSpec document (from PipeSpec or directly), verify:

- [ ] `orchspec_version` is `"1.0"`
- [ ] `pipeline_id` is lowercase snake_case, matches pattern `^[a-z0-9][a-z0-9_-]*$`
- [ ] `description` is non-empty, ≤ 4096 characters
- [ ] `metadata` has all four required fields: `name`, `owner`, `domain`, `complexity`
- [ ] `components` is an array with ≥1 items, each having: `id`, `name`, `category`, `executor.type`
- [ ] Component `id` values are lowercase snake_case
- [ ] Component `category` values are PascalCase (`Extractor`, `Transformer`, etc.)
- [ ] `executor.type` values are snake_case (`python_script`, `http_request`, `container`, etc.)
- [ ] Category/executor combinations are compatible (see section 5 compatibility table)
- [ ] `flow.pattern` is a valid FlowPattern enum
- [ ] `flow.entry_points` has ≥1 item, each referencing a valid component `id`
- [ ] `flow.edges` use valid component `id` values for `from` and `to`
- [ ] Flow is acyclic (for `sequential`, `parallel`, `dag` patterns)
- [ ] All components are reachable from entry points
- [ ] Flow is a single connected component (no disconnected subgraphs)
- [ ] Sequential flow has no branching (fan-out ≤ 1)
- [ ] All `integration_id` references in I/O specs resolve to `integrations[].id`
- [ ] All `integrations_used` values resolve to `integrations[].id`
- [ ] All `secret_ref`, `username_secret`, `password_secret` resolve to `secrets[].name`
- [ ] If `schedule.enabled` is `true`, `schedule.cron` is present
- [ ] Retry policy `multiplier` > 1 when strategy is `exponential`
- [ ] Retry policy `max_delay_seconds` ≥ `delay_seconds` when both are set
- [ ] **No embedded secret values** — secrets reference names only
- [ ] `additionalProperties: false` — only use fields defined in the schema
- [ ] Integrations sorted by `id`, components in topological order, edges sorted by `(from, to)`

---

## 17. Common Mistakes to Avoid

| Mistake | Fix |
|---------|-----|
| Using PipeSpec executor names (`python`, `http`, `docker`) | Use OrchSpec names: `python_script`, `http_request`, `container` |
| Using PipeSpec parameter types (`string`, `int`) | Use UPPERCASE: `STRING`, `INT` |
| Using PascalCase component IDs | Use lowercase snake_case: `extract_api`, not `ExtractAPI` |
| Forgetting `executor` is an object with `type` field | PipeSpec has flat `executor_type`; OrchSpec nests `executor.type` |
| Adding a `flow_structure.nodes` map | OrchSpec has no nodes map — components are the nodes |
| Using combined `io_spec[]` with `direction` field | OrchSpec splits into `inputs[]` and `outputs[]` |
| Nesting integrations under `integrations.connections` | OrchSpec has flat `integrations[]` array |
| Missing `metadata.owner` or `metadata.domain` | All four metadata fields are required in OrchSpec |
| Embedding secret values (passwords, tokens, keys) | Use `secrets[]` references by name; never embed values |
| Edge `from`/`to` references component names instead of IDs | Use component `id` values (lowercase snake_case) |
| Creating disconnected subgraphs | Ensure all components are reachable from entry points (SEM012) |
| Sequential flow with fan-out > 1 | Use `dag` or `parallel` pattern instead |
| Forgetting `schedule.cron` when `schedule.enabled` is true | Add a valid cron expression |
| Leaving unused `integrations_used` references | Remove or declare the integration |
| Schema-property typos (e.g., `executer` vs `executor`) | The schema is strict — check spelling against this guide |
| Including `$schema` or `$id` in the document | OrchSpec documents do not include JSON Schema meta-properties |

---

## 18. Determinism — Canonical Ordering Rules

OrchSpec documents are deterministically serialized. When generating, apply these ordering rules:

1. **Integrations** sorted by `id` ascending.
2. **Components** in topological order from `flow.edges` (root → leaf), then alphabetical by `id` for tie-breaks.
3. **Edges** sorted by `(from, to)` ascending.
4. **Object keys** sorted alphabetically at serialization time.
5. **Omit** null/empty optional fields from output.
6. No runtime-generated timestamps or random IDs.

---

## 19. Validation & Iterative Repair

If validation reveals errors, follow this repair loop:

1. **Read the validation errors** — each error includes a `code` (SCHEMA_* or SEM0xx), a `message`, and a JSON path.
2. **Fix schema errors first** — missing required fields, type mismatches, enum typos, extra properties.
3. **Fix semantic errors** — graph issues (SEM001–SEM003, SEM008, SEM011–SEM012), cross-references (SEM002, SEM004–SEM007), schedule (SEM009), compatibility (SEM010), retry coherence (SEM013).
4. **Check determinism** — run `make golden-check` to ensure output matches canonical fixtures.
5. **Re-validate** after each fix.

For tooling: use `orchspec-validate` CLI or the Python API (`validate_orchspec`) to check conformance.

### Validation Commands

```bash
# Validate an OrchSpec document
orchspec-validate pipeline.orchspec.yaml

# Validate with strict mode (SEM010 promoted to error)
orchspec-validate pipeline.orchspec.yaml --strict

# Output JSON report
orchspec-validate pipeline.orchspec.yaml --json-report

# Diff two OrchSpec documents (semantic comparison)
orchspec-diff old.orchspec.yaml new.orchspec.yaml --json-report
```

### Semantic Error Quick Reference

| Code | Check |
|------|-------|
| SEM001 | Entry points exist in components |
| SEM002 | Edge endpoints reference known components |
| SEM003 | DAG acyclicity |
| SEM004 | `integrations_used` references declared integrations |
| SEM005 | I/O `integration_id` references declared integrations |
| SEM006 | Secret references resolve to declared secrets |
| SEM007 | Unique component/integration IDs |
| SEM008 | Sequential flow fan-out ≤ 1 |
| SEM009 | `schedule.enabled` requires `schedule.cron` |
| SEM010 | Category/executor compatibility |
| SEM011 | All components reachable from entry points |
| SEM012 | No disconnected subgraphs |
| SEM013 | Retry policy coherence |
