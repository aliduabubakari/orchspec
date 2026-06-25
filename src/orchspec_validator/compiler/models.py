"""Compiler models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompileOptions:
    strict: bool = False
    enforce_profile: bool = True


class CompileError(ValueError):
    """Raised when PipeSpec input cannot be compiled deterministically."""

    def __init__(self, code: str, message: str, path: str = "$") -> None:
        self.code = code
        self.message = message
        self.path = path
        super().__init__(f"{code} {path}: {message}")
