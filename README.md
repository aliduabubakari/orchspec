# OrchSpec

**Orchestration Specification** — a platform-agnostic pipeline abstraction standard with a deterministic compiler, multi-layered validator, semantic diff engine, and an extensible adapter framework for projecting pipelines onto any orchestrator.

OrchSpec is not tied to a single execution engine. It defines a canonical intermediate representation (IR) that can be consumed, validated, diffed, and projected to imperative or declarative orchestrators through pluggable adapters.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Core Components](#core-components)
  - [OrchSpec Schema v1.0](#orchspec-schema-v10)
  - [PipeSpec → OrchSpec Compiler](#pipespec--orchspec-compiler)
  - [Validation Engine](#validation-engine)
  - [Semantic Diff](#semantic-diff)
  - [Adapter Framework](#adapter-framework)
- [Schema Extensibility](#schema-extensibility)
- [Adding a New Orchestrator Adapter](#adding-a-new-orchestrator-adapter)
- [Extending the Schema](#extending-the-schema)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [Repository Layout](#repository-layout)
- [Development](#development)
- [License](#license)

---

## Quick Start

### Install

```bash
pip install orchspec
```

### Compile a PipeSpec document into OrchSpec

```bash
pipespec2orchspec input.json --out output.yaml --format yaml --strict
```

### Validate an OrchSpec document

```bash
orchspec-validate output.yaml --strict --json-report
```

### Compare two OrchSpec documents semantically

```bash
orchspec-diff old.yaml new.yaml --json-report
```

---

## Core Components

### OrchSpec Schema v1.0

The canonical JSON Schema is at [`spec/orchspec_schema_v1.json`](spec/orchspec_schema_v1.json). It defines the structure for:

| Section | Purpose |
|---------|---------|
| `metadata` | Pipeline identity, ownership, domain, complexity, tags, labels, provenance |
| `schedule` | Cron-based scheduling with catch-up and concurrency controls |
| `parameters` | Typed parameters (STRING, INT, FLOAT, BOOLEAN, DATETIME, DATE, FILE, JSON, ARRAY) with defaults and constraints |
| `variables` | Free-form key-value runtime variables |
| `secrets` | Secret references with sensitivity levels and env-var fallbacks |
| `integrations` | External system connections: API, database, filesystem, object store, message queue, SMTP, custom |
| `container_runtime` | Default container image, resource requests/limits, security context, volumes |
| `components` | The pipeline steps — extractors, transformers, loaders, quality checks, notifiers, sensors, custom |
| `flow` | DAG topology with entry points, edges, conditions, parallelism groups |
| `error_handling` | Failure policies and notification channels (log, email, Slack, webhook, PagerDuty) |
| `observability` | Logging, metrics, and data lineage configuration |
| `ots_export` | Optional Open Transformation Standard export mappings |
| `provenance` | Source file, generator, and timestamp metadata |

The schema is designed with **extensibility as a first-class concern**. See [Schema Extensibility](#schema-extensibility) for details.

### PipeSpec → OrchSpec Compiler

The `pipespec2orchspec` compiler deterministically converts PipeSpec v1.0 JSON documents into OrchSpec documents.

**Key properties:**
- **Deterministic**: Same input + same compiler version = identical output (byte-for-byte)
- **Strict mode** (`--strict`): Rejects unknown executor types and invalid inputs with stable error codes
- **Canonical ordering**: Components are topologically sorted; all object keys are serialized canonically
- **Formal mapping spec**: All transformation rules are declared in [`spec/mappings/pipespec_to_orchspec_v1.json`](spec/mappings/pipespec_to_orchspec_v1.json)

**Executor type mapping:**

| PipeSpec | OrchSpec |
|----------|----------|
| `python` | `python_script` |
| `http` | `http_request` |
| `sql` | `sql` |
| `bash` | `bash` |
| `container` | `container` |
| `email` | `email` |
| unknown | `custom` (error in `--strict`) |

### Validation Engine

`orchspec-validate` runs two layers of validation:

1. **Schema validation** — Structural compliance against the JSON Schema.
2. **Semantic validation** — Cross-field and inter-component integrity rules:

| Rule | Check |
|------|-------|
| SEM001 | `components[].id` uniqueness |
| SEM002 | `flow.edges` reference valid component IDs |
| SEM003 | `flow.entry_points` exist in components |
| SEM004 | `integrations[].id` uniqueness |
| SEM005 | `integrations_used` references valid integration IDs |
| SEM006 | `secrets[].name` uniqueness |
| SEM007 | `parameters` keys are valid identifiers |
| SEM008 | `pipeline_id` matches pattern `^[a-z0-9][a-z0-9_-]*$` |
| SEM009 | `flow.pattern` is consistent with `flow.edges` |
| SEM010 | `ots_export.component_mappings` reference valid components |
| SEM011 | No unreachable components in the flow graph |
| SEM012 | No disconnected subgraphs |
| SEM013 | Retry policy coherence (strategy, delay, multiplier consistency) |

With `--strict`, warnings (SEM010) are promoted to errors.

### Semantic Diff

`orchspec-diff` compares two OrchSpec documents and reports structural and semantic changes:

- Component additions, removals, and renames
- Edge topology changes
- Parameter and integration changes
- Executor type migrations
- Retry policy and timeout modifications

Designed for CI/CD pipelines to gate deployment of pipeline changes.

### Adapter Framework

OrchSpec's adapter framework enables **projecting** an OrchSpec document onto any target orchestrator. This is the core extensibility mechanism for multi-orchestrator support.

**Built-in stub adapters:**

| Adapter | Target | Runtime Style |
|---------|--------|---------------|
| `AirflowAdapter` | Apache Airflow | imperative |
| `PrefectAdapter` | Prefect | imperative |
| `DagsterAdapter` | Dagster | imperative |
| `KestraAdapter` | Kestra | declarative |
| `ArgoAdapter` | Argo Workflows | declarative |
| `KubeflowAdapter` | Kubeflow Pipelines | declarative |
| `FlyteAdapter` | Flyte | declarative |

Each adapter implements the [`OrchspecAdapter` Protocol](src/orchspec_validator/adapters/interface.py):

```python
class OrchspecAdapter(Protocol):
    def capability(self) -> AdapterCapability: ...
    def validate_invariants(self, orchspec_doc: dict) -> list[str]: ...
    def project(self, orchspec_doc: dict) -> ProjectionResult: ...
```

See [Adding a New Orchestrator Adapter](#adding-a-new-orchestrator-adapter) for a step-by-step guide.

---

## Schema Extensibility

OrchSpec is designed to grow with your needs. There are multiple extension points that allow you to adapt the spec without forking the core.

### Extension Point 1: Custom Executor Types

The `executor.type` enum supports a `custom` value. When you use `custom`, you can attach arbitrary metadata through `executor.custom_class`:

```json
{
  "id": "my_component",
  "executor": {
    "type": "custom",
    "custom_class": "com.enterprise.KafkaConnector"
  }
}
```

In `--strict` compiler mode, unknown executor types raise `COMP012`. In non-strict mode, they are coerced to `custom` with the original type preserved in provenance.

### Extension Point 2: Custom Component Categories

Use the `Custom` component category for domain-specific pipeline steps that fall outside the standard ETL taxonomy:

```json
{
  "id": "feature_engineer",
  "category": "Custom",
  "name": "ML Feature Engineering"
}
```

### Extension Point 3: Custom Integration Types

The `integration.type` enum includes a `custom` value for external systems not covered by the standard types (api, database, filesystem, object_store, message_queue, smtp):

```json
{
  "id": "redis_cache",
  "type": "custom",
  "protocol": "redis",
  "host": "cache.internal"
}
```

### Extension Point 4: Labels and Tags

`metadata.labels` is a free-form `object` (string → string) and `metadata.tags` is a `string[]`. These carry arbitrary key-value metadata and taxonomies without schema changes:

```json
{
  "metadata": {
    "labels": {
      "cost_center": "eng-42",
      "compliance": "sox",
      "data_classification": "pii"
    },
    "tags": ["finance", "daily", "critical"]
  }
}
```

### Extension Point 5: Adapter Projections

The adapter framework is the primary mechanism for adding new orchestrator targets. Each adapter can interpret OrchSpec fields through its own lens, validate target-specific invariants, and emit target-specific IR. See the [adapter guide](#adding-a-new-orchestrator-adapter).

### Extension Point 6: JSON Schema `$ref` Overrides

The OrchSpec schema uses JSON Schema draft-07. You can extend the schema by creating a wrapper schema that `$ref`s the canonical schema and adds `allOf` or `anyOf` constraints for domain-specific fields. This keeps your extensions separate from the upstream spec while maintaining validation compatibility.

### Extension Point 7: OTS Export

The optional `ots_export` section maps OrchSpec components to Open Transformation Standard types (`sql_transformation`, `python_model`, `external_source`, `external_sink`), enabling direct projection into transformation layers like dbt™ or SQLMesh.

---

## Adding a New Orchestrator Adapter

### Step 1: Create the adapter class

In `src/orchspec_validator/adapters/stubs.py`, add a new class that extends `_BaseStubAdapter`:

```python
class TemporalAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="temporal", runtime_style="imperative")
```

### Step 2: Register the adapter

In `src/orchspec_validator/adapters/registry.py`, add your adapter to `get_default_adapters()`:

```python
from orchspec_validator.adapters.stubs import TemporalAdapter

def get_default_adapters() -> list[OrchspecAdapter]:
    return [
        AirflowAdapter(),
        PrefectAdapter(),
        # ... existing adapters ...
        TemporalAdapter(),
    ]
```

### Step 3: Customize the projection

Override `validate_invariants()` and `project()` to emit real target-specific IR instead of the stub:

```python
class TemporalAdapter(_BaseStubAdapter):
    def validate_invariants(self, orchspec_doc: dict) -> list[str]:
        violations = super().validate_invariants(orchspec_doc)
        # Add Temporal-specific checks
        for comp in orchspec_doc.get("components", []):
            if comp.get("executor", {}).get("type") == "sql":
                violations.append(
                    f"Component {comp['id']}: Temporal does not natively support SQL executor; "
                    f"wrap in a container activity"
                )
        return violations

    def project(self, orchspec_doc: dict) -> ProjectionResult:
        violations = self.validate_invariants(orchspec_doc)
        if violations:
            raise ValueError(f"Cannot project to {self.target_name}: {', '.join(violations)}")

        # Generate Temporal workflow + activity definitions
        workflow = self._build_temporal_workflow(orchspec_doc)
        return ProjectionResult(
            target=self.target_name,
            artifact_type="temporal_workflow",
            content=workflow,
        )
```

### Step 4: Add adapter-specific tests

Create tests that verify your adapter's projection invariants and output. See `tests/test_adapters.py` for patterns.

---

## Extending the Schema

If you need domain-specific fields beyond what labels/tags provide:

1. **Create a wrapper schema** (e.g., `my_org/orchspec_extended_v1.json`):
   ```json
   {
     "$schema": "http://json-schema.org/draft-07/schema#",
     "allOf": [
       { "$ref": "../spec/orchspec_schema_v1.json" },
       {
         "properties": {
           "compliance": {
             "type": "object",
             "properties": {
               "gdpr_scope": { "type": "boolean" },
               "retention_days": { "type": "integer" }
             }
           }
         }
       }
     ]
   }
   ```

2. **Validate against your extended schema** instead of the canonical one:
   ```python
   from orchspec_validator.validation.schema import validate_against_schema

   validate_against_schema(doc, schema_path="my_org/orchspec_extended_v1.json")
   ```

3. **The canonical schema uses `additionalProperties: false`** at the top level, so extended fields must be added through a wrapper schema with `allOf` — this is intentional to keep the core spec clean and versioned independently.

---

## CLI Reference

### `pipespec2orchspec`

```bash
pipespec2orchspec <input.json> [options]
```

| Option | Description |
|--------|-------------|
| `--out PATH` | Output file path |
| `--format yaml\|json` | Output format (default: json) |
| `--strict` | Reject unknown executor types and invalid inputs |

### `orchspec-validate`

```bash
orchspec-validate <input.yaml|input.json> [options]
```

| Option | Description |
|--------|-------------|
| `--strict` | Promote compatibility warnings to errors |
| `--json-report` | Emit machine-readable JSON report |

Exit codes: `0` = valid, `1` = runtime error, `2` = validation failure.

### `orchspec-diff`

```bash
orchspec-diff <old.yaml|old.json> <new.yaml|new.json> [options]
```

| Option | Description |
|--------|-------------|
| `--json-report` | Emit machine-readable JSON diff report |

---

## Python API

```python
from orchspec_validator import (
    CompileOptions,
    compile_pipespec_to_orchspec,
    validate_orchspec,
    semantic_diff_orchspec,
    get_default_adapters,
)

# Compile PipeSpec → OrchSpec
orchspec = compile_pipespec_to_orchspec(
    pipespec_doc,
    options=CompileOptions(strict=True)
)

# Validate (schema + semantic)
report = validate_orchspec(orchspec, strict=True)
print(f"Valid: {report.valid}, Errors: {len(report.errors)}")

# Semantic diff
diff = semantic_diff_orchspec(orchspec_a, orchspec_b)
for change in diff.changes:
    print(f"{change.severity}: {change.description}")

# List available target adapters
for adapter in get_default_adapters():
    cap = adapter.capability()
    print(f"{cap.target} ({cap.runtime_style}) — {len(cap.supported_executors)} executors")

# Project to a specific target
airflow = get_default_adapters()[0]
result = airflow.project(orchspec)
print(result.artifact_type, result.target)
```

---

## Repository Layout

```
.
├── spec/
│   ├── orchspec_schema_v1.json          # Canonical JSON Schema
│   ├── orchspec-spec-v1.md              # Normative spec
│   ├── pipespec_profile_v1.json         # Strict PipeSpec input profile
│   └── mappings/
│       └── pipespec_to_orchspec_v1.json # Machine-readable compiler rules
├── docs/
│   ├── compiler-guide.md                # Field mapping reference
│   ├── field-reference.md               # Schema field documentation
│   ├── execution-modes.md               # Imperative vs declarative targets
│   └── changelog.md                     # Version history
├── src/orchspec_validator/
│   ├── __init__.py                      # Public API surface
│   ├── io.py                            # Document loading (JSON/YAML)
│   ├── compiler/
│   │   ├── api.py                       # compile_pipespec_to_orchspec
│   │   ├── mapper.py                    # Field-level transformation
│   │   ├── mapping_spec.py              # Mapping spec loader
│   │   ├── profile.py                   # Strict profile validator
│   │   └── models.py                    # CompileOptions, error types
│   ├── validation/
│   │   ├── api.py                       # validate_orchspec entry point
│   │   ├── schema.py                    # JSON Schema validation
│   │   ├── semantic.py                  # SEM001–SEM013 rules
│   │   └── models.py                    # ValidationReport, Issue
│   ├── diff/
│   │   ├── api.py                       # semantic_diff_orchspec entry point
│   │   ├── core.py                      # Diff engine
│   │   └── models.py                    # DiffReport, Change
│   ├── adapters/
│   │   ├── interface.py                 # OrchspecAdapter Protocol
│   │   ├── registry.py                  # Adapter discovery
│   │   ├── stubs.py                     # Built-in stub adapters
│   │   ├── invariants.py                # Shared projection invariants
│   │   └── models.py                    # AdapterCapability, ProjectionResult
│   └── cli/
│       ├── compile.py                   # pipespec2orchspec CLI
│       ├── validate.py                  # orchspec-validate CLI
│       └── diff.py                      # orchspec-diff CLI
├── tests/
│   ├── fixtures/
│   │   ├── orchspec/                    # Valid OrchSpec fixtures
│   │   ├── invalid_orchspec/            # Invalid fixtures for validation tests
│   │   └── golden/                      # Deterministic compiler output snapshots
│   └── test_*.py                        # Unit and integration tests
├── samples/pipespecs/                    # Sample PipeSpec inputs
├── tools/
│   └── golden.py                        # Golden file checker/updater
├── pyproject.toml
├── Makefile
└── .github/workflows/ci.yml
```

---

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
make test

# Check golden files
make golden-check

# Update golden files (after intentional mapping changes)
make update-golden

# Lint
ruff check .

# Type check
mypy src
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
