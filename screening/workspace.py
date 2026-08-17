"""Screening workspace service."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from domain.actors import ActorType
from domain.screening import ScreeningDecision, ScreeningRecord


class ScreeningRecordNotFoundError(Exception):
    """Raised when a literature record ID is not present in the workspace."""

    def __init__(self, literature_record_id: UUID) -> None:
        self.literature_record_id = literature_record_id
        super().__init__(
            f"No screening record found for literature record ID: {literature_record_id}"
        )


@dataclass
class ScreeningProgress:
    total: int
    screened: int
    pending: int
    percentage: float


class ScreeningWorkspace:
    """
    Manages screening records for a deduplicated literature collection.

    - Creates one PENDING ScreeningRecord per unique literature record ID.
    - Supports explicit researcher decision updates.
    - Never infers, generates, or invents decisions.
    - Never calls AI.
    """

    def __init__(self) -> None:
        # Preserves insertion order; UUID → ScreeningRecord
        self._records: dict[UUID, ScreeningRecord] = {}
        # Tracks insertion order
        self._insertion_order: list[UUID] = []

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def add_record(self, literature_record_id: UUID) -> ScreeningRecord:
        """
        Add a literature record to the workspace as PENDING.

        If the ID already exists, return the existing record without change.
        """
        if literature_record_id in self._records:
            return self._records[literature_record_id]

        record = ScreeningRecord(
            literature_record_id=literature_record_id,
            decision=ScreeningDecision.PENDING,
        )
        self._records[literature_record_id] = record
        self._insertion_order.append(literature_record_id)
        return record

    def add_records(self, literature_record_ids: list[UUID]) -> list[ScreeningRecord]:
        """Add multiple literature records in order."""
        return [self.add_record(lid) for lid in literature_record_ids]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, literature_record_id: UUID) -> ScreeningRecord:
        """Return the screening record for the given literature record ID."""
        if literature_record_id not in self._records:
            raise ScreeningRecordNotFoundError(literature_record_id)
        return self._records[literature_record_id]

    def list_records(self) -> list[ScreeningRecord]:
        """Return all screening records in deterministic insertion order."""
        return [self._records[lid] for lid in self._insertion_order]

    def pending(self) -> list[ScreeningRecord]:
        """Return all PENDING screening records in insertion order."""
        return [
            self._records[lid]
            for lid in self._insertion_order
            if self._records[lid].decision == ScreeningDecision.PENDING
        ]

    # ------------------------------------------------------------------
    # Decision update
    # ------------------------------------------------------------------

    def set_decision(
        self,
        literature_record_id: UUID,
        decision: ScreeningDecision,
        decided_by: ActorType,
        reason: str | None = None,
        notes: str | None = None,
        decided_at: datetime | None = None,
    ) -> ScreeningRecord:
        """
        Record an explicit researcher screening decision.

        Never infers or generates a decision.
        Reuses ScreeningRecord validation for correctness.
        """
        if literature_record_id not in self._records:
            raise ScreeningRecordNotFoundError(literature_record_id)

        effective_decided_at = decided_at
        if decision != ScreeningDecision.PENDING and effective_decided_at is None:
            effective_decided_at = datetime.now(timezone.utc)

        # Construct a new ScreeningRecord — reuses domain validation
        updated = ScreeningRecord(
            id=self._records[literature_record_id].id,
            literature_record_id=literature_record_id,
            decision=decision,
            reason=reason,
            notes=notes,
            decided_at=effective_decided_at,
            decided_by=decided_by if decision != ScreeningDecision.PENDING else None,
        )
        self._records[literature_record_id] = updated
        return updated

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def counts(self) -> dict[str, int]:
        """Return counts for all four screening states. Never omits zero values."""
        result = {
            ScreeningDecision.PENDING.value: 0,
            ScreeningDecision.INCLUDE.value: 0,
            ScreeningDecision.EXCLUDE.value: 0,
            ScreeningDecision.MAYBE.value: 0,
        }
        for rec in self._records.values():
            result[rec.decision.value] += 1
        return result

    def total(self) -> int:
        """Return the number of unique literature records in the workspace."""
        return len(self._records)

    def screened_count(self) -> int:
        """Return the number of records with a final decision (INCLUDE, EXCLUDE, MAYBE)."""
        screened = {ScreeningDecision.INCLUDE, ScreeningDecision.EXCLUDE, ScreeningDecision.MAYBE}
        return sum(1 for r in self._records.values() if r.decision in screened)

    def progress(self) -> ScreeningProgress:
        """Return deterministic screening progress. Never divides by zero."""
        total = self.total()
        screened = self.screened_count()
        pending = total - screened
        percentage = (screened / total * 100.0) if total > 0 else 0.0
        return ScreeningProgress(
            total=total,
            screened=screened,
            pending=pending,
            percentage=percentage,
        )
