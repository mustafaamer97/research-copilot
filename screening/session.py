"""
Screening Session — Sprint 3.

ScreeningSession owns:
- a stable session ID
- ScreeningCriteria
- ScreeningWorkspace
- ScreeningHistory  (Task 17: audit trail of explicit decision changes)

Task 18: ScreeningSession.decide()
    Atomically updates the workspace decision and records the history entry.
    The researcher calls decide() once; the session ensures consistency.

No AI. No external APIs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from screening.criteria import ScreeningCriteria
from screening.decision import ScreeningDecision
from screening.history import ScreeningDecisionHistoryEntry, ScreeningHistory
from screening.workspace import ScreeningRecordNotFoundError, ScreeningWorkspace


class ScreeningSession:
    """
    A screening session for one research project screening pass.

    Owns:
    - session_id: stable UUID string
    - criteria: ScreeningCriteria
    - workspace: ScreeningWorkspace
    - history: ScreeningHistory (append-only audit log of decision changes)

    Responsibilities:
    - Delegates workspace operations to ScreeningWorkspace.
    - Records explicit researcher decision changes via record_decision_change().
    - Provides decide() to atomically update workspace + history in one call.
    - Does NOT auto-generate history entries outside of decide().
    - Does NOT modify ScreeningWorkspace internals directly.
    """

    def __init__(
        self,
        criteria: ScreeningCriteria,
        workspace: ScreeningWorkspace,
        session_id: Optional[str] = None,
    ) -> None:
        if not isinstance(criteria, ScreeningCriteria):
            raise TypeError(
                f"Expected ScreeningCriteria, got {type(criteria).__name__}."
            )
        if not isinstance(workspace, ScreeningWorkspace):
            raise TypeError(
                f"Expected ScreeningWorkspace, got {type(workspace).__name__}."
            )

        self._session_id: str = session_id if session_id else str(uuid.uuid4())
        self._criteria: ScreeningCriteria = criteria
        self._workspace: ScreeningWorkspace = workspace
        self._history: ScreeningHistory = ScreeningHistory()

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    # ------------------------------------------------------------------
    # Criteria
    # ------------------------------------------------------------------

    @property
    def criteria(self) -> ScreeningCriteria:
        return self._criteria

    # ------------------------------------------------------------------
    # Workspace delegation
    # ------------------------------------------------------------------

    @property
    def workspace(self) -> ScreeningWorkspace:
        return self._workspace

    # ------------------------------------------------------------------
    # History — Task 17
    # ------------------------------------------------------------------

    @property
    def history(self) -> ScreeningHistory:
        """The append-only audit log of explicit decision changes."""
        return self._history

    def record_decision_change(self, entry: ScreeningDecisionHistoryEntry) -> None:
        """
        Record an explicit researcher decision change into the session history.

        The caller is responsible for constructing the ScreeningDecisionHistoryEntry.

        This method does NOT call set_decision() on the workspace.
        It does NOT auto-generate entries.
        It does NOT modify workspace internals.

        Raises:
            TypeError: if entry is not a ScreeningDecisionHistoryEntry.
        """
        if not isinstance(entry, ScreeningDecisionHistoryEntry):
            raise TypeError(
                f"Expected ScreeningDecisionHistoryEntry, "
                f"got {type(entry).__name__}."
            )
        self._history.record(entry)

    # ------------------------------------------------------------------
    # Coordinated decision — Task 18
    # ------------------------------------------------------------------

    def decide(
        self,
        literature_record_id: str,
        new_decision: ScreeningDecision,
        changed_by: str,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ScreeningDecisionHistoryEntry:
        """
        Apply a researcher screening decision atomically.

        Steps (in order):
        1. Retrieve the current ScreeningRecord from the workspace.
        2. Reject if new_decision == current decision (no-op).
        3. Apply new_decision to the workspace via set_decision().
        4. Construct a ScreeningDecisionHistoryEntry.
        5. Record the entry into session history.
        6. Return the entry.

        Args:
            literature_record_id: The stable ID of the literature record.
            new_decision: The researcher's new decision.
            changed_by: Identifier of the researcher making the decision.
            reason: Optional reason for the decision.
            notes: Optional additional notes.

        Returns:
            The ScreeningDecisionHistoryEntry that was recorded.

        Raises:
            ScreeningRecordNotFoundError: if the record is not in the workspace.
            ValueError: if new_decision == current decision (no change).
            TypeError: if new_decision is not a ScreeningDecision.
            ValueError: if changed_by is empty.
        """
        if not isinstance(new_decision, ScreeningDecision):
            raise TypeError(
                f"Expected ScreeningDecision, got {type(new_decision).__name__}."
            )

        # Step 1: retrieve current record (raises ScreeningRecordNotFoundError if missing)
        record = self._workspace.get(literature_record_id)
        previous_decision = record.decision

        # Step 2: reject no-op
        if previous_decision == new_decision:
            raise ValueError(
                f"Decision did not change for record '{literature_record_id}': "
                f"current decision is already '{new_decision.value}'."
            )

        # Step 3: apply to workspace
        self._workspace.set_decision(literature_record_id, new_decision)

        # Step 4: construct history entry
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id=literature_record_id,
            previous_decision=previous_decision,
            new_decision=new_decision,
            changed_at=datetime.now(tz=timezone.utc),
            changed_by=changed_by,
            reason=reason,
            notes=notes,
        )

        # Step 5: record into history
        self._history.record(entry)

        # Step 6: return entry
        return entry
