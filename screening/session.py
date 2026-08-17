"""
Screening Session — Sprint 3.

ScreeningSession owns:
- a stable session ID
- ScreeningCriteria
- ScreeningWorkspace
- ScreeningHistory  (Task 17: audit trail of explicit decision changes)

The session delegates screening operations to ScreeningWorkspace.
History is recorded explicitly via record_decision_change().
No AI. No external APIs.
"""

from __future__ import annotations

import uuid
from typing import List

from screening.criteria import ScreeningCriteria
from screening.history import ScreeningDecisionHistoryEntry, ScreeningHistory
from screening.workspace import ScreeningWorkspace


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
    - Does NOT auto-generate history entries.
    - Does NOT modify ScreeningWorkspace internals.
    """

    def __init__(
        self,
        criteria: ScreeningCriteria,
        workspace: ScreeningWorkspace,
        session_id: str | None = None,
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

        The caller is responsible for constructing the ScreeningDecisionHistoryEntry
        with the correct previous_decision, new_decision, changed_by, and changed_at.

        This method does NOT call set_decision() on the workspace.
        It does NOT auto-generate entries.
        It does NOT modify workspace internals.

        Raises:
            TypeError: if entry is not a ScreeningDecisionHistoryEntry.
        """
        if not isinstance(entry, ScreeningDecisionHistoryEntry):
            raise TypeError(
                f"Expected ScreeningDecisionHistoryEntry, got {type(entry).__name__}."
            )
        self._history.record(entry)
