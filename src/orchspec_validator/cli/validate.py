"""CLI for OrchSpec validation."""

from __future__ import annotations

import argparse
import json
import sys

from orchspec_validator.io import load_document
from orchspec_validator.validation.api import validate_orchspec


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orchspec-validate")
    p.add_argument("input", help="OrchSpec JSON/YAML file")
    p.add_argument("--semantic-only", action="store_true", help="Reserved for compatibility")
    p.add_argument("--strict", action="store_true", help="Promote compatibility warnings to errors")
    p.add_argument("--json-report", action="store_true", help="Emit report as JSON")
    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        doc = load_document(args.input)
        report = validate_orchspec(doc, strict=args.strict)
        if args.json_report:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(f"valid={report.valid} errors={len(report.errors)} warnings={len(report.warnings)}")
            for issue in report.errors:
                print(f"ERROR {issue.code} {issue.path}: {issue.message}")
            for issue in report.warnings:
                print(f"WARN  {issue.code} {issue.path}: {issue.message}")
        return 0 if report.valid else 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
