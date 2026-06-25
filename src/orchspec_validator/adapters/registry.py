"""Adapter registry."""

from __future__ import annotations

from orchspec_validator.adapters.interface import OrchspecAdapter
from orchspec_validator.adapters.stubs import (
    AirflowAdapter,
    ArgoAdapter,
    DagsterAdapter,
    FlyteAdapter,
    KestraAdapter,
    KubeflowAdapter,
    PrefectAdapter,
)


def get_default_adapters() -> list[OrchspecAdapter]:
    return [
        AirflowAdapter(),
        PrefectAdapter(),
        DagsterAdapter(),
        KestraAdapter(),
        ArgoAdapter(),
        KubeflowAdapter(),
        FlyteAdapter(),
    ]
