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

    def validate_invariants(self, orchspec_doc: dict) -> list[str]:
        violations = super().validate_invariants(orchspec_doc)
        for idx, comp in enumerate(orchspec_doc.get("components", [])):
            exec_type = (comp.get("executor") or {}).get("type")
            if exec_type == "sql":
                violations.append(
                    f"component[{idx}] '{comp.get('id')}': SQL executor requires "
                    f"apache-airflow-providers-common-sql package"
                )
            if exec_type == "container":
                image = comp.get("image_override") or (comp.get("executor") or {}).get("image")
                if not image:
                    violations.append(
                        f"component[{idx}] '{comp.get('id')}': container executor "
                        f"requires an image (set image_override or executor.image)"
                    )
        return violations

    def project(self, orchspec_doc: dict) -> ProjectionResult:
        from orchspec_validator.adapters.airflow_projector import project_to_airflow
        violations = self.validate_invariants(orchspec_doc)
        # Only block on critical violations (missing required fields, etc.)
        critical = [v for v in violations if "missing" in v.lower()]
        if critical:
            raise ValueError(f"Cannot project to {self.target_name}: {', '.join(critical)}")
        return project_to_airflow(orchspec_doc)


class PrefectAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="prefect", runtime_style="imperative")

    def project(self, orchspec_doc: dict) -> ProjectionResult:
        from orchspec_validator.adapters.prefect_projector import project_to_prefect
        violations = self.validate_invariants(orchspec_doc)
        critical = [v for v in violations if "missing" in v.lower()]
        if critical:
            raise ValueError(f"Cannot project to {self.target_name}: {', '.join(critical)}")
        return project_to_prefect(orchspec_doc)


class DagsterAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="dagster", runtime_style="imperative")

    def project(self, orchspec_doc: dict) -> ProjectionResult:
        from orchspec_validator.adapters.dagster_projector import project_to_dagster
        violations = self.validate_invariants(orchspec_doc)
        critical = [v for v in violations if "missing" in v.lower()]
        if critical:
            raise ValueError(f"Cannot project to {self.target_name}: {', '.join(critical)}")
        return project_to_dagster(orchspec_doc)


class KestraAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="kestra", runtime_style="declarative")


class ArgoAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="argo", runtime_style="declarative")

    def project(self, orchspec_doc: dict) -> ProjectionResult:
        from orchspec_validator.adapters.argo_projector import project_to_argo
        violations = self.validate_invariants(orchspec_doc)
        critical = [v for v in violations if "missing" in v.lower()]
        if critical:
            raise ValueError(f"Cannot project to {self.target_name}: {', '.join(critical)}")
        return project_to_argo(orchspec_doc)


class KubeflowAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="kubeflow", runtime_style="declarative")


class FlyteAdapter(_BaseStubAdapter):
    def __init__(self) -> None:
        super().__init__(target_name="flyte", runtime_style="declarative")
