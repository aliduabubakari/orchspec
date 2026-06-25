# PipeSpec Test Corpus

This folder contains short PipeSpec fixtures for testing OrchSpec compilation and validation.

## Structure
- `valid/`: should compile and validate cleanly.
- `invalid_compile/`: should fail during `pipespec2orchspec --strict` with `COMP` errors.
- `invalid_semantic/`: should compile but fail `orchspec-validate` with `SEM` errors.

## Suggested usage

Compile strict:

```bash
pipespec2orchspec samples/pipespecs/valid/ok_sequential.json --out /tmp/out.json --strict
```

Expected compile failure:

```bash
pipespec2orchspec samples/pipespecs/invalid_compile/comp001_unknown_executor.json --out /tmp/out.json --strict
```

Semantic failure flow:

```bash
pipespec2orchspec samples/pipespecs/invalid_semantic/sem009_schedule_without_cron.json --out /tmp/out.json --strict
orchspec-validate /tmp/out.json
```

## Fixture index

### Valid
- `valid/ok_sequential.json`: Minimal sequential ETL.
- `valid/ok_parallel_like_dag.json`: Small DAG with fan-out/fan-in.
- `valid/ok_notifier.json`: Pipeline ending in notifier/email task.

### Invalid compile (strict)
- `invalid_compile/comp001_unknown_executor.json` -> `COMP001`
- `invalid_compile/comp003_missing_component_name.json` -> `COMP003`
- `invalid_compile/comp004_missing_component_category.json` -> `COMP004`
- `invalid_compile/comp006_missing_io_kind.json` -> `COMP006`
- `invalid_compile/comp007_missing_integration_id.json` -> `COMP007`
- `invalid_compile/comp008_bad_version.json` -> `COMP008`
- `invalid_compile/comp009_empty_components.json` -> `COMP009`
- `invalid_compile/comp010_missing_pipeline_name.json` -> `COMP010`
- `invalid_compile/comp011_missing_pipeline_description.json` -> `COMP011`

### Invalid semantic (after compile)
- `invalid_semantic/sem001_missing_entrypoint_component.json` -> `SEM001`
- `invalid_semantic/sem002_edge_unknown_target.json` -> `SEM002`
- `invalid_semantic/sem004_missing_declared_integration.json` -> `SEM004`
- `invalid_semantic/sem008_sequential_branching.json` -> `SEM008`
- `invalid_semantic/sem009_schedule_without_cron.json` -> `SEM009`
