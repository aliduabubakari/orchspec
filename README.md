# OrchSpec

OrchSpec is a standalone standard for pipeline orchestration abstraction.

This repository publishes:
- OrchSpec v1.0 schema and specification
- Deterministic `pipespec2orchspec` compiler
- `orchspec-validate` schema+semantic validator
- `orchspec-diff` semantic comparator
- Adapter interfaces/stubs for future multi-orchestrator projection

## Install

```bash
pip install orchspec-validator
```

## CLI

```bash
pipespec2orchspec input.json --out output.yaml --format yaml --strict
orchspec-validate output.yaml --json-report
orchspec-validate output.yaml --strict
orchspec-diff old.yaml new.yaml --json-report
```

## Python API

```python
from orchspec_validator import CompileOptions, compile_pipespec_to_orchspec, validate_orchspec, semantic_diff_orchspec

orchspec = compile_pipespec_to_orchspec(pipespec_doc, options=CompileOptions(strict=True))
report = validate_orchspec(orchspec, strict=True)
diff = semantic_diff_orchspec(orchspec_a, orchspec_b)
```

## Compiler Contracts

- Strict PipeSpec profile: `spec/pipespec_profile_v1.json`
- Formal mapping spec: `spec/mappings/pipespec_to_orchspec_v1.json`

## Golden Regression Workflow

Check golden files:

```bash
PYTHONPATH=src python tools/golden.py --check
# or
make golden-check
```

Update golden files intentionally after mapping-rule changes:

```bash
PYTHONPATH=src python tools/golden.py --update-golden
# or
make update-golden
```

## Repository Layout

- `spec/` canonical schema, profile, and mapping specs
- `docs/` field references and compiler rules
- `src/orchspec_validator/` package source
- `tests/` unit/integration and golden determinism tests
- `samples/pipespecs/` short corpus for valid/invalid scenario testing
