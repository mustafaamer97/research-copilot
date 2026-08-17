"""Screening criteria domain contract."""
from pydantic import BaseModel, field_validator


class InclusionCriteria(BaseModel):
    """Researcher-defined criteria that a study must satisfy to be included."""
    model_config = {"frozen": True}

    description: str

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("InclusionCriteria description must not be empty or whitespace.")
        return v


class ExclusionCriteria(BaseModel):
    """Researcher-defined criteria that disqualify a study from inclusion."""
    model_config = {"frozen": True}

    description: str

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ExclusionCriteria description must not be empty or whitespace.")
        return v


class ScreeningCriteria(BaseModel):
    """
    The complete screening criteria contract for a screening process.

    Represents researcher-defined rules only.
    Never generates, infers, or modifies scientific criteria.
    """
    model_config = {"frozen": True}

    inclusion_criteria: InclusionCriteria
    exclusion_criteria: ExclusionCriteria
