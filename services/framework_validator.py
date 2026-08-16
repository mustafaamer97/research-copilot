"""Deterministic framework validation engine."""
from enum import Enum

from pydantic import BaseModel

from domain.framework import FrameworkType, ResearchFramework


class FrameworkValidationStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class FrameworkValidationResult(BaseModel):
    status: FrameworkValidationStatus
    framework_type: FrameworkType
    missing_components: list[str]


_PICO_ORDER = ["Population", "Intervention", "Comparator", "Outcome"]
_PECO_ORDER = ["Population", "Exposure", "Comparator", "Outcome"]

_PICO_FIELDS = {
    "Population": "population",
    "Intervention": "intervention",
    "Comparator": "comparator",
    "Outcome": "outcome",
}

_PECO_FIELDS = {
    "Population": "population",
    "Exposure": "exposure",
    "Comparator": "comparator",
    "Outcome": "outcome",
}


def validate_framework(framework: ResearchFramework) -> FrameworkValidationResult:
    """
    Inspect a ResearchFramework and return a deterministic validation result.

    Never mutates the framework.
    Never invents missing information.
    """
    if framework.type == FrameworkType.PICO:
        order = _PICO_ORDER
        field_map = _PICO_FIELDS
    else:
        order = _PECO_ORDER
        field_map = _PECO_FIELDS

    missing = [
        label
        for label in order
        if getattr(framework, field_map[label]) is None
    ]

    status = (
        FrameworkValidationStatus.COMPLETE
        if not missing
        else FrameworkValidationStatus.INCOMPLETE
    )

    return FrameworkValidationResult(
        status=status,
        framework_type=framework.type,
        missing_components=missing,
    )
