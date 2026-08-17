"""Literature search strategy domain contract."""
from pydantic import BaseModel, Field

from domain.framework import FrameworkType


class LiteratureSearchStrategy(BaseModel):
    model_config = {"frozen": True}

    framework_type: FrameworkType
    population_terms: list[str] = Field(default_factory=list)
    intervention_terms: list[str] = Field(default_factory=list)
    exposure_terms: list[str] = Field(default_factory=list)
    comparator_terms: list[str] = Field(default_factory=list)
    outcome_terms: list[str] = Field(default_factory=list)
    boolean_query: str | None = None
