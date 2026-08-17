"""
Screening Decision History Contract — Tasks 15 & 16.

Task 15: ScreeningDecisionHistoryEntry
    Immutable record of a single explicit researcher decision change.

Task 16: ScreeningHistory
    Append-only log of ScreeningDecisionHistoryEntry objects.
    Provides retrieval by literature_record_id and full audit access.
    No AI. No external APIs. No ScreeningWorkspace modification.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

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


class ScreeningHistory:
    """
    Append-only log of ScreeningDecisionHistoryEntry objects.

    Stores the complete audit trail of explicit researcher screening
    decision changes across all literature records in a screening session.

    Rules:
    - Only ScreeningDecisionHistoryEntry objects are accepted.
    - Entries are stored in insertion order.
    - Retrieval by literature_record_id returns entries in insertion order.
    - No entry can be removed or modified after recording.
    - No AI. No external API. No ScreeningWorkspace modification.
    """

    def __init__(self) -> None:
        self._entries: List[ScreeningDecisionHistoryEntry] = []
        self._index: Dict[str, List[ScreeningDecisionHistoryEntry]] = {}

    def record(self, entry: ScreeningDecisionHistoryEntry) -> None:
        """
        Record a decision change entry.

        Raises:
            TypeError: if entry is not a ScreeningDecisionHistoryEntry.
        """
        if not isinstance(entry, ScreeningDecisionHistoryEntry):
            raise TypeError(
                f"Expected ScreeningDecisionHistoryEntry, got {type(entry).__name__}."
            )
        self._entries.append(entry)
        self._index.setdefault(entry.literature_record_id, []).append(entry)

    def for_record(self, literature_record_id: str) -> List[ScreeningDecisionHistoryEntry]:
        """
        Return all history entries for a given literature_record_id,
        in insertion order.

        Returns an empty list if no entries exist for that ID.
        """
        return list(self._index.get(literature_record_id, []))

    def all_entries(self) -> List[ScreeningDecisionHistoryEntry]:
        """
        Return all history entries across all records, in insertion order.
        """
        return list(self._entries)

    def count(self) -> int:
        """Total number of recorded history entries."""
        return len(self._entries)

    def count_for_record(self, literature_record_id: str) -> int:
        """Number of history entries for a given literature_record_id."""
        return len(self._index.get(literature_record_id, []))

    def has_history(self, literature_record_id: str) -> bool:
        """Return True if any history entries exist for the given ID."""
        return literature_record_id in self._index and bool(
            self._index[literature_record_id]
        )
