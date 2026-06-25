"""Stub adapters for future orchestrator projections."""

from __future__ import annotations

from dataclasses import dataclass

from orchspec_validator.adapters.invariants import validate_projection_invariants
from orchspec_validator.adapters.models import AdapterCapability, ProjectionResult


@dataclass
class _BaseStubAdapter:
    target_name: str
    runtime_style: str

    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            target=self.target_name,
            runtime_style=self.runtime_style,
            supported_executors=(
                "python_script",
                "container",
                "http_request",
                "sql",
                "email",
                "bash",
                "custom",
            ),
        )

    def validate_invariants(self, orchspec_doc: dict) -> list[str]:
        return validate_projection_invariants(orchspec_doc)

    def project(self, orchspec_doc: dict) -> ProjectionResult:
        violations = self.validate_invariants(orchspec_doc)
        if violations:
            raise ValueError(f"Cannot project to {self.target_name}: {', '.join(violations)}")

        # Stub IR to lock interface before full generators are implemented.
        return ProjectionResult(
            target=self.target_name,
            artifact_type="stub_ir",
            content={
                "pipeline_id": orchspec_doc.get("pipeline_id"),
                "target": self.target_name,
                "runtime_style": self.runtime_style,
                "component_count": len(orchspec_doc.get("components", [])),
            },
        )


class AirflowAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="airflow", runtime_style="imperative")


class PrefectAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="prefect", runtime_style="imperative")


class DagsterAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="dagster", runtime_style="imperative")


class KestraAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="kestra", runtime_style="declarative")


class ArgoAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="argo", runtime_style="declarative")


class KubeflowAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="kubeflow", runtime_style="declarative")


class FlyteAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="flyte", runtime_style="declarative")
