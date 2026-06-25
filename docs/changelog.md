# Changelog

## 1.1.0 - 2026-06-25
- Initial OrchSpec release: full namespace, compiler, validator, diff, and adapter framework
- Renamed package to `orchspec` (PyPI)
- Extensively documented schema extensibility patterns and adapter framework
- 7 documented extension points: custom executors, categories, integrations, labels/tags, adapters, schema $ref overrides, OTS export

## 1.0.0 (formerly OPOS v1.1.0) - 2026-03-08
- Added strict PipeSpec profile schema and early compiler rejection (`COMP012`)
- Added machine-readable mapping spec (`spec/mappings/pipespec_to_orchspec_v1.json`)
- Expanded semantic validation with:
  - `SEM011` unreachable components
  - `SEM012` disconnected subgraphs
  - `SEM013` retry policy coherence checks
- Added strict semantic mode (`orchspec-validate --strict`) where `SEM010` is promoted to error
- Added adapter interfaces, registry, and stub adapters for multi-orchestrator projection

## 1.0.0 - 2026-03-04
- Added OrchSpec v1.0 schema and spec
- Added deterministic PipeSpec -> OrchSpec compiler
- Added `orchspec-validate` schema + semantic validation
- Added `orchspec-diff` semantic comparator
- Added fixtures, tests, and CI
