"""
Screening Decision History Contract — Task 15.

Represents one explicit researcher decision change for a literature record.
Immutable. No AI. No external APIs. No LiteratureRecord embedded.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from screening.decision import ScreeningDecision


class ScreeningDecisionHistoryEntry(BaseModel):
    """
    Immutable record of a single explicit screening decision change.

    Represents exactly one researcher decision change.
    previous_decision != new_decision is enforced.

    Only literature_record_id is stored — no LiteratureRecord is embedded.
    No AI. No external API.

    Initial creation of a ScreeningRecord as PENDING does NOT produce
    a ScreeningDecisionHistoryEntry.
    """

    literature_record_id: str = Field(
        ...,
        description="Stable ID of the literature record. No full record embedded.",
    )
    previous_decision: ScreeningDecision = Field(
        ...,
        description="The decision before this change.",
    )
    new_decision: ScreeningDecision = Field(
        ...,
        description="The decision after this change.",
    )
    changed_at: datetime = Field(
        ...,
        description="When the change occurred. Must be timezone-aware.",
    )
    changed_by: str = Field(
        ...,
        description="Researcher identifier. Required. Non-empty.",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional reason for the decision change.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional additional notes.",
    )

    model_config = {"frozen": True}

    @field_validator("literature_record_id")
    @classmethod
    def literature_record_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("literature_record_id must not be empty.")
        return v

    @field_validator("changed_by")
    @classmethod
    def changed_by_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("changed_by must not be empty.")
        return v

    @field_validator("changed_at")
    @classmethod
    def changed_at_must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError(
                "changed_at must be timezone-aware. "
                "Use datetime with tzinfo=timezone.utc."
            )
        return v

    @model_validator(mode="after")
    def decisions_must_differ(self) -> ScreeningDecisionHistoryEntry:
        if self.previous_decision == self.new_decision:
            raise ValueError(
                f"previous_decision and new_decision must differ. "
                f"Both are '{self.previous_decision.value}'."
            )
        return self
