"""Screening session domain contract."""
from __future__ import annotations

from uuid import UUID, uuid4

from domain.actors import ActorType
from domain.screening import ScreeningDecision, ScreeningRecord
from screening.criteria import ScreeningCriteria
from screening.workspace import ScreeningProgress, ScreeningWorkspace


class ScreeningSession:
    """
    One screening context binding criteria to a workspace of literature records.

    - Criteria are required and fixed for the session.
    - Workspace manages all screening record state.
    - Never automates decisions.
    - Never calls AI.
    """

    def __init__(
        self,
        criteria: ScreeningCriteria,
        literature_record_ids: list[UUID] | None = None,
        session_id: UUID | None = None,
    ) -> None:
        if criteria is None:
            raise ValueError("ScreeningSession requires valid ScreeningCriteria.")

        self._id: UUID = session_id if session_id is not None else uuid4()
        self._criteria: ScreeningCriteria = criteria
        self._workspace: ScreeningWorkspace = ScreeningWorkspace()

        if literature_record_ids:
            self._workspace.add_records(literature_record_ids)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def criteria(self) -> ScreeningCriteria:
        return self._criteria

    @property
    def workspace(self) -> ScreeningWorkspace:
        return self._workspace

    # ------------------------------------------------------------------
    # Delegation — workspace operations
    # ------------------------------------------------------------------

    def get_screening_record(self, literature_record_id: UUID) -> ScreeningRecord:
        return self._workspace.get(literature_record_id)

    def set_decision(
        self,
        literature_record_id: UUID,
        decision: ScreeningDecision,
        decided_by: ActorType,
        reason: str | None = None,
        notes: str | None = None,
        decided_at=None,
    ) -> ScreeningRecord:
        return self._workspace.set_decision(
            literature_record_id=literature_record_id,
            decision=decision,
            decided_by=decided_by,
            reason=reason,
            notes=notes,
            decided_at=decided_at,
        )

    def pending(self) -> list[ScreeningRecord]:
        return self._workspace.pending()

    def counts(self) -> dict[str, int]:
        return self._workspace.counts()

    def progress(self) -> ScreeningProgress:
        return self._workspace.progress()

    def total(self) -> int:
        return self._workspace.total()
