# OrchSpec Field Reference

See canonical schema: `spec/orchspec_schema_v1.json`.

Key required top-level fields:
- `orchspec_version`
- `pipeline_id`
- `description`
- `metadata`
- `components`
- `flow`

Semantic validation is enforced by `orchspec-validate` with `SEM001..SEM010` rules.
