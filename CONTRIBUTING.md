# Contributing to OrchSpec

Thank you for contributing! OrchSpec is a specification and toolkit for pipeline orchestration. Contributions can take many forms: new adapters, schema extensions, validation rules, documentation, or bug fixes.

---

## Development Setup

### Prerequisites

- Python ≥ 3.10
- Git

### Install

```bash
git clone https://github.com/aliduabubakari/orchspec.git
cd orchspec
pip install -e ".[dev]"
```

### Run Tests

```bash
make test
# or
pytest -q
```

### Lint & Type Check

```bash
ruff check .
mypy src
```

### Golden Files

The compiler's output is checked against golden files to ensure determinism:

```bash
make golden-check     # verify nothing changed
make update-golden    # update after intentional mapping changes
```

---

## Repository Layout

```
src/orchspec_validator/
├── __init__.py           # Public API surface
├── io.py                 # JSON/YAML loading
├── compiler/             # PipeSpec → OrchSpec compiler
│   ├── api.py            # compile_pipespec_to_orchspec()
│   ├── mapper.py         # Field-level transformation
│   ├── mapping_spec.py   # Machine-readable mapping loader
│   ├── profile.py        # Strict PipeSpec profile validator
│   └── models.py         # CompileOptions, CompileError
├── validation/           # OrchSpec validation
│   ├── api.py            # validate_orchspec()
│   ├── schema.py         # JSON Schema validation
│   ├── semantic.py       # SEM001–SEM021 rules
│   └── models.py         # ValidationReport, ValidationIssue
├── diff/                 # Semantic diff
│   ├── api.py            # semantic_diff_orchspec()
│   ├── core.py           # Diff engine
│   └── models.py         # DiffReport, DiffItem
├── adapters/             # Multi-orchestrator projection
│   ├── interface.py      # OrchspecAdapter Protocol
│   ├── registry.py       # Adapter discovery
│   ├── stubs.py          # Built-in adapters
│   ├── invariants.py     # Shared projection invariants
│   ├── airflow_projector.py  # Real Airflow DAG generator
│   └── models.py         # AdapterCapability, ProjectionResult
└── cli/                  # Command-line entry points
    ├── compile.py        # pipespec2orchspec
    ├── validate.py       # orchspec-validate
    └── diff.py           # orchspec-diff
```

---

## How to Contribute

### 1. Adding a New Orchestrator Adapter

Adapters project OrchSpec documents onto specific orchestrator targets.

**Step 1: Create the adapter class**

In `src/orchspec_validator/adapters/stubs.py`, add a class that extends `_BaseStubAdapter`:

```python
class MyOrchestratorAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="my_orchestrator", runtime_style="imperative")

    def validate_invariants(self, orchspec_doc: dict) -> list[str]:
        violations = super().validate_invariants(orchspec_doc)
        # Add target-specific checks here
        return violations

    def project(self, orchspec_doc: dict) -> ProjectionResult:
        violations = self.validate_invariants(orchspec_doc)
        critical = [v for v in violations if "missing" in v.lower()]
        if critical:
            raise ValueError(f"Cannot project: {', '.join(critical)}")
        # Generate target-specific IR
        return ProjectionResult(
            target=self.target_name,
            artifact_type="my_orch_dag",
            content={"source": "...", "dag_id": orchspec_doc.get("pipeline_id")},
        )
```

**Step 2: Register the adapter**

In `src/orchspec_validator/adapters/registry.py`, add your adapter to `get_default_adapters()`:

```python
from orchspec_validator.adapters.stubs import MyOrchestratorAdapter

def get_default_adapters() -> list[OrchspecAdapter]:
    return [
        AirflowAdapter(),
        # ... existing adapters ...
        MyOrchestratorAdapter(),
    ]
```

**Step 3: Add tests**

Create tests in `tests/test_adapters.py` or a new file. Verify:

- `capability()` returns correct target and runtime style
- `validate_invariants()` catches target-specific issues
- `project()` emits syntactically valid target IR
- Basic, multi-branch, and scheduled pipeline fixtures all compile

**Step 4: Document**

- Add your adapter to the table in `README.md` and `spec/orchspec-spec-v1.md`
- If the adapter has a real projection (not a stub), add a note to `docs/changelog.md`

---

### 2. Adding a Semantic Validation Rule

Validation rules live in `src/orchspec_validator/validation/semantic.py`.

**Step 1: Choose a rule number**

Rules follow the pattern `SEM0xx`. Check the current highest number in the file and increment. Document your rule in `spec/orchspec-spec-v1.md` under §5.2.

**Step 2: Implement the rule**

Add your validation logic inside `validate_semantics()`. Rules that detect objective problems should go into `errors`; advisory checks should go into `warnings`.

```python
# SEM022: example rule
for idx, comp in enumerate(doc.get("components", [])):
    if some_condition:
        errors.append(
            ValidationIssue(
                "SEM022",
                "description of the violation",
                f"$.components[{idx}].field_name",
            )
        )
```

**Step 3: Add tests**

Add both positive (should pass) and negative (should fail) test cases in `tests/test_semantic_strict.py`. Use the `_base_doc()` fixture pattern.

**Step 4: Document**

Add the rule to the validation table in `README.md` and `spec/orchspec-spec-v1.md`.

---

### 3. Extending the Schema

The canonical schema is at `spec/orchspec_schema_v1.json`. For domain-specific extensions, create a **wrapper schema** — do not modify the canonical schema directly. This keeps the core spec clean and independently versioned.

**Wrapper schema pattern:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "allOf": [
    { "$ref": "../orchspec_schema_v1.json" },
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

For changes to the canonical schema:
1. Open an issue describing the proposed change
2. Discuss backward compatibility impact
3. If accepted, update the schema, spec doc, README, and validation rules
4. Bump the schema version following [SemVer](https://semver.org)

---

### 4. Adding a Compiler Error Code

Error codes follow the pattern `COMP0xx`. To add one:

1. Define it in `src/orchspec_validator/compiler/models.py` or raise `CompileError(code, message, path)` in `mapper.py`
2. Add a test in `tests/test_compiler_edge_cases.py` that triggers the error
3. Document the code in `spec/orchspec-spec-v1.md` §7.4

---

### 5. Documentation

Documentation lives in:
- `README.md` — project overview, quick start, reference
- `spec/orchspec-spec-v1.md` — formal specification
- `docs/` — compiler guide, field reference, execution modes

When adding features:
- Update the formal specification with semantics
- Update the README with usage examples
- Update the changelog

---

## Testing Guidelines

### Every feature needs tests

| Feature type | Minimum tests |
|-------------|---------------|
| New SEM rule | 2 tests (positive + negative) |
| New COMP code | 1 test (triggers the error) |
| New adapter | 3 tests (basic, invariants, multi-branch) |
| Compiler change | Golden regression + edge case |
| Schema change | Validation test (rejects invalid, accepts valid) |

### Run before pushing

```bash
make test                # unit + integration
make golden-check        # deterministic output
ruff check .             # lint
mypy src                 # type check
```

---

## Pull Request Process

1. **Open an issue** describing what you want to change and why
2. **Fork the repository** and create a feature branch
3. **Make your changes** with tests and documentation
4. **Run the full test suite** (see above)
5. **Open a PR** against `main` with:
   - A clear description
   - References to the issue
   - A summary of what changed
6. **CI will run** lint, type check, golden check, and tests automatically
7. A maintainer will review and merge

### Commit Style

- Use present tense, imperative mood: "Add SEM022" not "Added SEM022"
- Keep commits focused: one logical change per commit
- Reference issues in commit messages when applicable

---

## Code of Conduct

Be respectful, constructive, and inclusive. Harassment or disrespectful behavior will not be tolerated.

---

## Questions?

Open an issue on GitHub or start a discussion. We're happy to help.
