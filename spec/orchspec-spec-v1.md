# OrchSpec Specification v1.0

OrchSpec v1.0 defines a platform-agnostic pipeline abstraction that can be compiled to imperative and declarative orchestrators.

## Normative Artifacts
- Schema: `spec/orchspec_schema_v1.json`
- Compiler mapping: `docs/compiler-guide.md`

## Validation Model
Documents are valid only when:
1. They satisfy the JSON Schema.
2. They pass semantic rules SEM001..SEM010.

## Determinism Requirement
Given the same PipeSpec input bytes and compiler version, generated OrchSpec output must be semantically identical and canonically serialized.
