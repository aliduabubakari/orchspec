"""Adapter domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdapterCapability:
    target: str
    runtime_style: str
    supported_executors: tuple[str, ...]


@dataclass
class ProjectionResult:
    target: str
    artifact_type: str
    content: dict[str, Any]
