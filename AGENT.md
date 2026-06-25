# AGENT.md — OrchSpec Development Guide

> **Guidance for AI coding agents working on the OrchSpec project.**
>
> OrchSpec (the Orchestrator-Agnostic Canonical Specification) is a universal pipeline abstraction layer.
> It provides deterministic PipeSpec → canonical-form compilation, schema+semantic validation, semantic diffing,
> and adapter stubs for future multi-orchestrator projection (Airflow, Prefect, Dagster, Kestra, Argo, KFP, Flyte).
>
> This file covers architecture, conventions, workflows, and common tasks.

---

## 1. Project Identity

| Item | Value |
|------|-------|
| **Project name** | OrchSpec (the Orchestrator-Agnostic Canonical Specification) |
| **Package name** | `opos-validator` |
| **Import name** | `opos_validator` |
| **CLI entries** | `pipespec2opos` / `opos-validate` / `opos-diff` |
| **Python** | ≥3.10 |
| **Build system** | setuptools |
| **Schema version** | OPOS Schema v1.0 (`spec/opos_schema_v1.json`) |
| **License** | Apache-2.0 |

---

## 2. Repository Layout

```
opos/
├── spec/                                  # Canonical schema, profile, and mapping specs (normative)
│   ├── opos_schema_v1.json                #   THE normative OPOS JSON Schema (single source of truth)
│   ├── opos-spec-v1.md                    #   Specification overview document
│   ├── pipespec_profile_v1.json           #   Strict PipeSpec input profile enforced before compile
│   ├── mappings/
│   │   └── pipespec_to_opos_v1.json       #   Formal mapping spec driving compiler tables + invariants
│   └── examples/
│       ├── pipespec/                      #   Example PipeSpec input documents
│       └── opos/                          #   Compiled OPOS output examples (YAML)
│
├── src/opos_validator/                    # Python package
│   ├── __init__.py                        #   Public API surface (compile, validate, diff, adapters)
│   ├── io.py                              #   File I/O helpers
│   ├── compiler/                          #   PipeSpec → OPOS deterministic compiler
│   │   ├── __init__.py
│   │   ├── api.py                         #     compile_pipespec_to_opos() public entry
│   │   ├── mapper.py                      #     Core compilation implementation
│   │   ├── mapping_spec.py                #     Mapping spec loader + driven lookup tables
│   │   ├── profile.py                     #     PipeSpec input profile validation
│   │   └── models.py                      #     CompileOptions, CompileError
│   ├── validation/                        #   OPOS schema + semantic validation
│   │   ├── __init__.py
│   │   ├── api.py                         #     validate_opos() public entry
│   │   ├── schema.py                      #     JSON Schema validation wrapper
│   │   ├── semantic.py                    #     Semantic rule engine (SEM001–SEM013)
│   │   └── models.py                      #     ValidationIssue, ValidationReport
│   ├── diff/                              #   Semantic diff engine
│   │   ├── __init__.py
│   │   ├── api.py                         #     semantic_diff_opos() public entry
│   │   ├── core.py                        #     Diff implementation (meaning-level comparison)
│   │   └── models.py                      #     DiffReport, change classification
│   ├── adapters/                          #   Multi-orchestrator projection stubs
│   │   ├── __init__.py
│   │   ├── interface.py                   #     OposAdapter Protocol (capability, invariants, project)
│   │   ├── invariants.py                  #     Adapter invariant validation
│   │   ├── models.py                      #     AdapterCapability, ProjectionResult
│   │   ├── registry.py                    #     Adapter registry (get_default_adapters)
│   │   └── stubs.py                       #     Stub adapters for future targets
│   └── cli/                               #   User-facing CLI tools (Typer + Rich)
│       ├── __init__.py
│       ├── compile.py                     #     pipespec2opos
│       ├── validate.py                    #     opos-validate
│       └── diff.py                        #     opos-diff
│
├── samples/pipespecs/                     # Short PipeSpec corpus for taxonomy coverage
│   ├── valid/                             #   Clean-pass scenarios
│   ├── invalid_compile/                   #   Fixtures triggering COMP00x compile errors
│   └── invalid_semantic/                  #   Fixtures triggering SEM00x semantic errors
│
├── tests/                                 # Pytest test suite
│   ├── conftest.py                        #   Shared fixtures
│   ├── test_compiler.py                   #   Compiler unit tests
│   ├── test_validation.py                 #   Validation unit tests
│   ├── test_diff.py                       #   Diff unit tests
│   ├── test_adapters.py                   #   Adapter interface tests
│   ├── test_cli.py                        #   CLI end-to-end tests
│   ├── test_golden.py                     #   Deterministic golden regression tests
│   ├── test_profile_and_mapping.py        #   Profile + mapping spec tests
│   ├── test_semantic_strict.py            #   Strict mode semantic promotion tests
│   └── fixtures/                          #   Test fixtures (golden outputs, OPOS/PipeSpec samples)
│
├── docs/                                  # Documentation
│   ├── changelog.md
│   ├── compiler-guide.md                  #   Compiler mapping rules reference
│   ├── execution-modes.md                 #   Executor type reference
│   └── field-reference.md                 #   OPOS field definitions
│
├── tools/
│   └── golden.py                          #   Golden file check/update tool
│
├── pyproject.toml                         #   Project config, dependencies, entry points
├── Makefile                               #   Dev convenience targets (test, golden-check, update-golden)
├── technical.md                           #   Full technical design rationale
└── README.md                              #   User-facing docs + quickstart
```

---

## 3. Key Architecture Concepts

### 3.1 The Three-Layer Model

OrchSpec separates pipeline generation into three concerns:

1. **Understanding** — pipeline intent expressed as PipeSpec input.
2. **Normalizing** — deterministic compilation of PipeSpec into the canonical OrchSpec (OPOS) form.
3. **Projecting** — mapping OrchSpec into orchestrator-specific output (Airflow, Prefect, Dagster, Kestra, Argo, KFP, Flyte).

This repository implements layers 2 and 3 (stubs), along with validation and diff tooling.

### 3.2 Canonical Schema

- **`spec/opos_schema_v1.json`** is the single normative source of truth for OPOS structure.
- The compiler produces documents that MUST validate against this schema.
- `spec/pipespec_profile_v1.json` is a strict input profile applied *before* compilation begins.
- `spec/mappings/pipespec_to_opos_v1.json` is a formal mapping spec that drives compiler lookup tables and invariants.

### 3.3 Validation Layers

Validation is two-tiered:

1. **Schema validation** (`validation/schema.py`) — structural checks against `opos_schema_v1.json`. Error family: `SCHEMA_*`.
2. **Semantic validation** (`validation/semantic.py`) — cross-field and graph-level invariants that schema alone cannot enforce. Error family: `SEM001`–`SEM013`.

| Rule | Description |
|------|-------------|
| SEM001 | Entry points must exist in components |
| SEM002 | Each edge endpoint must reference known components |
| SEM003 | DAG must be acyclic for sequential/parallel/dag patterns |
| SEM004 | Component `integrations_used` must be declared |
| SEM005 | I/O `integration_id` must reference a declared integration |
| SEM006 | Referenced secrets must exist in the secrets list |
| SEM007 | Component/integration IDs must be unique |
| SEM008 | Sequential flow cannot branch (fan-out > 1) |
| SEM009 | Schedule enabled requires a cron expression |
| SEM010 | Category/executor compatibility (warning in normal mode, error in strict) |
| SEM011 | All components must be reachable from entry points |
| SEM012 | Flow graph must be a single weakly connected component (no disconnected subgraphs) |
| SEM013 | Retry configuration coherence (exponential multiplier > 1, max_delay ≥ delay) |

### 3.4 Strict Mode

`opos-validate --strict` promotes `SEM010` from a warning to an error. The compiler also supports a `CompileOptions(strict=True)` mode that:
- Enforces the PipeSpec input profile.
- Emits stable `COMP00x` error IDs for unknown executors, missing fields, empty lists, etc.
- Rejects unsupported PipeSpec versions.

### 3.5 Determinism Rules

Deterministic output is required for reproducible builds and reliable regression testing. Rules:

1. Integrations sorted by `id`.
2. Components ordered by topological DAG order, then deterministic tie-breaks.
3. Flow edges sorted by `(from, to)`.
4. Output object keys sorted at serialization time.
5. No runtime-generated timestamps unless present in input metadata.

### 3.6 Compile Error Taxonomy (`COMP00x`)

Stable error IDs make failures scriptable and testable:
- `COMP001` — unsupported executor type
- `COMP002` — missing component id
- `COMP003` — missing component name
- `COMP004` — missing component category
- `COMP005` — missing IO name
- `COMP006` — missing IO kind
- `COMP007` — missing integration id
- `COMP008` — unsupported PipeSpec version
- `COMP009` — empty component list
- `COMP010` — missing pipeline name
- `COMP011` — missing pipeline description

### 3.7 Semantic Diff Design

`opos-diff` compares OPOS documents at the meaning level, not raw text. Core behavior:

1. Compare top-level identity fields.
2. Compare components by stable `id`.
3. Compare integrations by stable `id`.
4. Compare DAG edges as logical sets.
5. Report field-level path changes.

Change classes:
- `breaking` — graph/task behavior impact.
- `non_breaking` — integration/catalog metadata impact.
- `informational` — metadata only.

### 3.8 Adapter Interface

`src/opos_validator/adapters/interface.py` defines the `OposAdapter` Protocol:

```python
class OposAdapter(Protocol):
    def capability(self) -> AdapterCapability: ...
    def validate_invariants(self, opos_doc: dict) -> list[str]: ...
    def project(self, opos_doc: dict) -> ProjectionResult: ...
```

Stub adapters live in `adapters/stubs.py` for future Airflow, Prefect, Dagster, Kestra, Argo, KFP, and Flyte targets.

---

## 4. Development Setup

```bash
# Run tests
PYTHONPATH=src pytest -q
# or
make test

# Check golden files (assert deterministic compiler output)
PYTHONPATH=src python tools/golden.py --check
# or
make golden-check

# Update golden files (after intentional mapping-rule changes)
PYTHONPATH=src python tools/golden.py --update-golden
# or
make update-golden
```

---

## 5. Code Conventions

### 5.1 Python Style

| Tool | Config |
|------|--------|
| **Formatter** | ruff format (line length 100) |
| **Linter** | ruff (rules: E, F, I, B, UP, N) |
| **Type checker** | mypy (mypy>=1.10.0) |

### 5.2 Module Conventions

- Use `from __future__ import annotations` in all modules.
- Use `from typing import Any` for generic dict handling (the schema/validation domain is inherently dynamic).
- Docstrings: concise module-level description, then function-level for public APIs.
- Keep `__init__.py` as the public API re-export surface. Implementation details go in sub-modules.

### 5.3 Public API Surface

From `src/opos_validator/__init__.py`:

```python
compile_pipespec_to_opos    # Compile PipeSpec dict → OPOS dict
validate_opos               # Validate OPOS dict (schema + semantics)
semantic_diff_opos          # Compare two OPOS dicts (meaning-level diff)
get_default_adapters        # Return default adapter registry
```

### 5.4 CLI Conventions

- Uses **Typer** + **Rich** for console output.
- Exit codes: `0` = success, non-zero for failures.
- `pipespec2opos` supports `--out`, `--format`, `--strict` flags.
- `opos-validate` supports `--json-report`, `--strict` flags.
- `opos-diff` supports `--json-report` flag.

---

## 6. Testing

```bash
PYTHONPATH=src pytest -q                    # Full suite
PYTHONPATH=src pytest tests/test_compiler.py  # Compiler unit tests
PYTHONPATH=src pytest tests/test_validation.py # Validation unit tests
PYTHONPATH=src pytest tests/test_diff.py     # Diff unit tests
PYTHONPATH=src pytest tests/test_adapters.py # Adapter interface tests
PYTHONPATH=src pytest tests/test_cli.py      # CLI end-to-end tests
PYTHONPATH=src pytest tests/test_golden.py   # Golden regression tests
PYTHONPATH=src pytest tests/test_profile_and_mapping.py  # Profile + mapping spec tests
PYTHONPATH=src pytest tests/test_semantic_strict.py      # Strict mode semantic tests
```

### Test fixture locations

- `tests/fixtures/pipespec/` — PipeSpec input fixtures for compilation tests.
- `tests/fixtures/opos/` — OPOS document fixtures for validation tests.
- `tests/fixtures/golden/` — canonical golden outputs for determinism regression.
- `tests/fixtures/invalid_opos/` — deliberately invalid OPOS documents.
- `samples/pipespecs/` — short corpus organized by scenario type (valid, invalid_compile, invalid_semantic).

### Test conventions

- Use `PYTHONPATH=src` to run tests against local source (no editable install required).
- Golden tests assert that the compiler output is byte-identical to canonical fixtures.
- Semantic rule tests should check for specific `rule_id` values (`SEM001`, `SEM002`, etc.) in the report output.
- Compiler error tests should assert specific `COMP` error codes.

---

## 7. Common Agent Tasks

### Add a new semantic rule

1. Add the rule function in `src/opos_validator/validation/semantic.py`.
2. Name it following the pattern of existing rules (e.g., `SEM014`).
3. Register it in the `validate_semantics()` function.
4. Add a test fixture in `samples/pipespecs/invalid_semantic/` that triggers the new rule.
5. Add a test in `tests/test_validation.py` or `tests/test_semantic_strict.py`.
6. If the rule should be promoted to an error in strict mode, add the condition in the `strict` branch.
7. Document the rule in `docs/changelog.md`.

### Add a new compiler error (`COMP` code)

1. Raise a `CompileError` with the new code in `src/opos_validator/compiler/mapper.py`.
2. Assign the next available number in the `COMP0xx` sequence.
3. Add a fixture in `samples/pipespecs/invalid_compile/` that triggers the error.
4. Add a test in `tests/test_compiler.py`.
5. Document the code in `technical.md` (section 8) and `docs/changelog.md`.

### Extend the compiler mapping

1. Edit `spec/mappings/pipespec_to_opos_v1.json` for mapping table changes.
2. Update `src/opos_validator/compiler/mapping_spec.py` if new loader logic is needed.
3. Update `src/opos_validator/compiler/mapper.py` for implementation logic.
4. Run `make golden-check` to detect any deterministic output changes.
5. If intentional, run `make update-golden` to regenerate golden fixtures.
6. Add/update tests in `tests/test_compiler.py`.

### Add a new adapter stub

1. Create the stub class in `src/opos_validator/adapters/stubs.py` implementing the `OposAdapter` Protocol.
2. Add invariant rules in `src/opos_validator/adapters/invariants.py`.
3. Register the adapter in `src/opos_validator/adapters/registry.py`.
4. Add tests in `tests/test_adapters.py`.

### Change the OPOS schema

1. Edit `spec/opos_schema_v1.json` (the normative schema).
2. Update `spec/opos-spec-v1.md` if the spec document needs updating.
3. Re-run tests: `make test`.
4. Update golden files if output shape changes: `make update-golden`.
5. Update `docs/field-reference.md` if field definitions change.
6. If the change is breaking, bump the schema version.

### Update dependencies

1. Edit `pyproject.toml` under `[project.dependencies]` or `[project.optional-dependencies].dev`.
2. No lockfile; dependencies are resolved at install time.

---

## 8. Design Constraints (DO NOT VIOLATE)

1. **Normative schema is king.** `spec/opos_schema_v1.json` is the only source of truth for OPOS structure. All validation MUST use it.
2. **Determinism is non-negotiable.** Given the same PipeSpec input bytes and compiler version, output MUST be semantically identical and canonically serialized. No runtime-generated timestamps, random IDs, or nondeterministic ordering.
3. **Error IDs must be stable.** Never reuse an old `COMP` or `SEM` code for a new meaning. Codes are part of the public contract.
4. **Strict PipeSpec profile enforced before compile.** `spec/pipespec_profile_v1.json` is validated before mapping begins.
5. **Adapter stubs are thin.** Adapters should rely on OPOS-normalized semantics. Do not add heavy logic — the adapter Protocol defines the contract; implementation details stay in the stub modules.
6. **Semantic checks can be additive but not destructive.** Add new `SEM` rules freely. Do not remove existing rules without a schema version bump.
7. **Golden tests are the regression contract.** Run `make golden-check` before committing. Only run `make update-golden` when mapping behavior intentionally changes.
8. **Preserve semantic meaning through normalization.** The compiler normalizes names/types to OPOS canonical enums, omits null/empty optional fields, and ensures deterministic ordering — but must never change pipeline intent.

---

## 9. Files to Read Before Major Changes

| File | When to read |
|------|-------------|
| `technical.md` | Understanding the full design rationale, architecture, and bounded scope |
| `spec/opos_schema_v1.json` | OPOS canonical schema structure |
| `spec/opos-spec-v1.md` | Specification overview and normative artifacts |
| `spec/mappings/pipespec_to_opos_v1.json` | Formal compiler mapping tables |
| `spec/pipespec_profile_v1.json` | Strict PipeSpec input profile |
| `docs/compiler-guide.md` | Compiler mapping rules and transformation reference |
| `docs/field-reference.md` | OPOS field definitions |
| `docs/execution-modes.md` | Executor type reference |
| `docs/changelog.md` | History of changes and extension rules |
| `README.md` | User-facing documentation and CLI quickstart |

---

## 10. Relationship to PipeSpec

OrchSpec consumes **PipeSpec** documents as input. PipeSpec is a separate project at `../pipespec/` that defines:

- The `pipespec-validator` package for generating, validating, and correcting PipeSpec pipeline description documents.
- The canonical PipeSpec schema (`pipespec_schema_v1.json`).
- LLM-assisted generation and correction tooling.

OrchSpec's `pipespec2opos` compiler expects input that validates against the PipeSpec schema. The two projects share the same pipeline domain model but operate at different layers: **PipeSpec** captures intent; **OrchSpec** normalizes it into an orchestrator-agnostic canonical form.

When changes span both projects (e.g., extending the PipeSpec schema), coordinate updates:
1. Update PipeSpec schema first.
2. Update OrchSpec's `spec/pipespec_profile_v1.json` and `spec/mappings/pipespec_to_opos_v1.json` to match.
3. Update the compiler, add fixtures, and regenerate golden files.
4. Run full test suites in both projects.
