"""Framework components and ResearchFramework contract."""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel


class FrameworkType(str, Enum):
    PICO = "PICO"
    PECO = "PECO"


class Population(BaseModel):
    description: str


class Intervention(BaseModel):
    description: str


class Exposure(BaseModel):
    description: str


class Comparator(BaseModel):
    description: str


class Outcome(BaseModel):
    description: str


class ResearchFramework(BaseModel):
    type: FrameworkType
    population: Population | None = None
    intervention: Intervention | None = None
    exposure: Exposure | None = None
    comparator: Comparator | None = None
    outcome: Outcome | None = None

    @property
    def is_complete(self) -> bool:
        # Import here to avoid circular import at module load time.
        from services.framework_validator import (
            FrameworkValidationStatus,
            validate_framework,
        )
        result = validate_framework(self)
        return result.status == FrameworkValidationStatus.COMPLETE
