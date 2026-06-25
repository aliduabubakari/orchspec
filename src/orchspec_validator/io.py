"""Shared I/O utilities for JSON/YAML documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


class InputError(ValueError):
    """Raised when an input document cannot be parsed."""


def load_document(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()

    try:
        if suffix in {".yaml", ".yml"}:
            data = yaml.safe_load(raw)
        else:
            data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise InputError(f"Failed to parse {p}: {exc}") from exc

    if not isinstance(data, dict):
        raise InputError(f"Root document in {p} must be an object")
    return data


def dump_document(doc: dict[str, Any], path: str | Path, fmt: str | None = None) -> None:
    p = Path(path)
    out_fmt = (fmt or p.suffix.lstrip(".") or "json").lower()
    if out_fmt in {"yml", "yaml"}:
        rendered = yaml.safe_dump(doc, sort_keys=True, allow_unicode=False)
    else:
        rendered = json.dumps(doc, indent=2, sort_keys=True)
    p.write_text(rendered + "\n", encoding="utf-8")
