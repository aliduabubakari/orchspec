# Changelog

All notable changes to OrchSpec are documented in this file.

---

## 1.0.0 — 2026-06-25

### Core

- **OrchSpec v1.0 schema** (`spec/orchspec_schema_v1.json`): platform-agnostic pipeline orchestration IR with 13 top-level sections covering metadata, schedule, parameters, secrets, integrations, container runtime, components, flow topology, error handling, observability, OTS export, and provenance.
- **Formal specification** (`spec/orchspec-spec-v1.md`): 11-section normative document defining execution semantics for all 5 flow patterns (sequential, parallel, DAG, conditional, loop), validation model, determinism guarantees, compilation contract, projection model, extensibility patterns, versioning policy, and security considerations.
- **Deterministic PipeSpec → OrchSpec compiler** (`pipespec2orchspec`): byte-identical output with canonical ordering, ID canonicalization, parameter type normalization, and strict input profile validation.
- **21 semantic validation rules** (SEM001–SEM021): structural integrity, reference integrity, category–executor compatibility, graph connectivity, configuration coherence, resource integrity, security coherence, I/O & data flow, condition expression syntax, integration compatibility, scheduling & timeouts, and declaration hygiene.
- **Schema + semantic validator** (`orchspec-validate`): two-layer validation with strict mode and JSON report output.
- **Semantic diff engine** (`orchspec-diff`): component-, edge-, and integration-aware diff with breaking/non-breaking classification.
- **IO utilities**: JSON and YAML document loading and canonical serialization.

### Adapter Framework

- **OrchspecAdapter Protocol**: pluggable interface with `capability()`, `validate_invariants()`, and `project()` methods.
- **7 built-in adapters**: Airflow (real projection), Prefect, Dagster, Kestra, Argo, Kubeflow, Flyte (stub projections).
- **Real Airflow 2.x DAG generator** (`airflow_projector.py`): TaskFlow API code emission for all 7 executor types (python_script → `@task`, http_request → `SimpleHttpOperator`, sql → `SQLExecuteQueryOperator`, email → `EmailOperator`, bash → `BashOperator`, container → `DockerOperator`, custom → `PythonOperator`). Handles schedule, retry, timeout, multi-branch DAGs (fan-out/fan-in), and correct TaskFlow `()` syntax in dependency chains.
- **Adapter invariants**: target-specific validation (SQL requires provider package, container requires image).
- **Shared projection invariants**: cross-adapter base checks for pipeline_id, metadata, components, and flow.

### Compiler

- **12 compile error codes** (COMP001–COMP012): unsupported executor types, missing required fields, version mismatch, empty components, profile violations.
- **Strict PipeSpec profile** (`spec/pipespec_profile_v1.json`): input contract with `additionalProperties: false` enforcement.
- **Machine-readable mapping spec** (`spec/mappings/pipespec_to_orchspec_v1.json`): executor type mapping, parameter type normalization, orchestrator invariants metadata.
- **Normalization**: schedule expressions, integration types (objectstore → object_store, queue → message_queue), IO formats (TXT → text), edge types, parameter types (integer → INT, float → FLOAT), authentication methods.
- **Canonical ordering**: topological sort (Kahn's algorithm), lexicographic key sorting, edge sorting by (from, to).

### Tests (97)

- **Compiler tests** (22): all COMP codes, all executor types, ID collision resolution, parameter type normalization, schedule normalization, IO format normalization, integration type normalization, determinism properties, provenance tracking, compile→validate roundtrip.
- **Semantic validation tests** (31): all SEM001–SEM021 with positive and negative cases.
- **Schema validation tests** (15): version rejection, missing fields, bad patterns, type errors, conditional/parallel flow patterns, structured report output.
- **Diff tests** (11): empty diff, edge/component/integration additions and removals, breaking vs non-breaking classification, deeply nested field changes.
- **Adapter tests** (10): all 7 adapters project correctly, Airflow DAG structural assertions, schedule+retry configuration, fan-out/fan-in DAGs, all executor type mappings, invariant violations, multiple entry points.
- **CLI integration test** (1): compile→validate→diff pipeline via subprocess.
- **Golden regression test** (1): byte-identical compiler output across 3 fixture pipelines.
- **Profile & mapping tests** (4): profile rejection, mapping spec integrity, full PipeSpec→OrchSpec→validate roundtrip, edge-case parameter normalization.

### Documentation

- **README.md**: project overview, PipeSpec→OrchSpec→Orchestrator pipeline diagram, quick start, core components reference, formal specification link, schema extensibility guide (7 extension points), step-by-step adapter development guide, CLI and Python API references, repository layout.
- **Compiler guide** (`docs/compiler-guide.md`): PipeSpec→OrchSpec field mapping, canonical ordering rules, normalization details, unsupported input policy.
- **Field reference** (`docs/field-reference.md`): schema field documentation.
- **Execution modes** (`docs/execution-modes.md`): imperative vs declarative target taxonomy.

### Infrastructure

- **CI/CD** (`.github/workflows/ci.yml`): lint (ruff), type check (mypy), golden check, unit tests, package build on PR and workflow dispatch.
- **Makefile**: `test`, `golden-check`, `update-golden` targets.
- **pyproject.toml**: `orchspec` package with CLI entry points (`orchspec-validate`, `orchspec-diff`, `pipespec2orchspec`), Apache 2.0 license, Python ≥ 3.10.
