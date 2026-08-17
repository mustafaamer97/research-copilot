"""Screening domain contract."""
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from domain.actors import ActorType


class ScreeningDecision(str, Enum):
    PENDING = "PENDING"
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    MAYBE = "MAYBE"


class ScreeningRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    literature_record_id: UUID
    decision: ScreeningDecision = ScreeningDecision.PENDING
    reason: str | None = None
    notes: str | None = None
    decided_at: datetime | None = None
    decided_by: ActorType | None = None

    @model_validator(mode="after")
    def validate_final_decision_completeness(self) -> "ScreeningRecord":
        final_decisions = {
            ScreeningDecision.INCLUDE,
            ScreeningDecision.EXCLUDE,
            ScreeningDecision.MAYBE,
        }
        if self.decision in final_decisions:
            if self.decided_at is None:
                raise ValueError(
                    f"decided_at is required when decision is {self.decision.value}."
                )
            if self.decided_by is None:
                raise ValueError(
                    f"decided_by is required when decision is {self.decision.value}."
                )
            if self.decided_at.tzinfo is None:
                raise ValueError(
                    "decided_at must be timezone-aware (UTC required)."
                )
        return self
