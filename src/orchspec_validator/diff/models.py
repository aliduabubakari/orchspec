"""Semantic diff models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class DiffItem:
    change_type: str
    path: str
    before: Any
    after: Any
    classification: str


@dataclass
class DiffReport:
    changes: list[DiffItem]

    def to_dict(self) -> dict[str, Any]:
        return {"changes": [asdict(c) for c in self.changes]}
