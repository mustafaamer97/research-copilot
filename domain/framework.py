"""Framework components and ResearchFramework contract."""
from enum import Enum
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
        if self.type == FrameworkType.PICO:
            return all([
                self.population is not None,
                self.intervention is not None,
                self.comparator is not None,
                self.outcome is not None,
            ])
        if self.type == FrameworkType.PECO:
            return all([
                self.population is not None,
                self.exposure is not None,
                self.comparator is not None,
                self.outcome is not None,
            ])
        return False
