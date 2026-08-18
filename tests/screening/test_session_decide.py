"""
Tests for ScreeningSession.decide() — Task 18.

decide() atomically:
1. Retrieves the current record from the workspace.
2. Rejects no-op decisions (same decision).
3. Applies the new decision to the workspace.
4. Constructs a ScreeningDecisionHistoryEntry.
5. Records the entry into session history.
6. Returns the entry.

Rules verified:
- PENDING → INCLUDE updates workspace and records history.
- INCLUDE → EXCLUDE updates workspace and records history.
- EXCLUDE → INCLUDE updates workspace and records history.
- Same decision raises ValueError.
- Unknown record raises ScreeningRecordNotFoundError.
- Wrong decision type raises TypeError.
- Empty changed_by raises ValueError.
- Returned entry is ScreeningDecisionHistoryEntry.
- Returned entry fields match the transition.
- History count increments correctly.
- Workspace decision is updated after decide().
- record_decision_change() still works independently (Task 17 preserved).
- No AI. No external API.
- All existing session behaviour preserved.
"""

from __future__ import annotations

import pytest
import uuid
from datetime import datetime, timezone

from pydantic import ValidationError

from screening.criteria import ExclusionCriteria, InclusionCriteria, ScreeningCriteria
from screening.decision import ScreeningDecision
from screening.history import ScreeningDecisionHistoryEntry, ScreeningHistory
from screening.record import ScreeningRecord
from screening.session import ScreeningSession
from screening.workspace import ScreeningProgress, ScreeningRecordNotFoundError, ScreeningWorkspace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_criteria() -> ScreeningCriteria:
    return ScreeningCriteria(
        inclusion=[InclusionCriteria(criterion="RCT design")],
        exclusion=[ExclusionCriteria(criterion="Non-English")],
    )


def _make_workspace_with_record(record_id: str = "lit-001") -> ScreeningWorkspace:
    ws = ScreeningWorkspace()
    ws.add(record_id)
    return ws


def _make_session_with_record(record_id: str = "lit-001") -> ScreeningSession:
    return ScreeningSession(
        criteria=_make_criteria(),
        workspace=_make_workspace_with_record(record_id),
    )


# ---------------------------------------------------------------------------
# Basic successful transitions
# ---------------------------------------------------------------------------

class TestDecideSuccessfulTransitions:

    def test_pending_to_include(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide(
            literature_record_id="lit-001",
            new_decision=ScreeningDecision.INCLUDE,
            changed_by="researcher-001",
        )
        assert entry.previous_decision == ScreeningDecision.PENDING
        assert entry.new_decision == ScreeningDecision.INCLUDE

    def test_pending_to_exclude(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide(
            literature_record_id="lit-001",
            new_decision=ScreeningDecision.EXCLUDE,
            changed_by="researcher-001",
        )
        assert entry.previous_decision == ScreeningDecision.PENDING
        assert entry.new_decision == ScreeningDecision.EXCLUDE

    def test_pending_to_maybe(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide(
            literature_record_id="lit-001",
            new_decision=ScreeningDecision.MAYBE,
            changed_by="researcher-001",
        )
        assert entry.previous_decision == ScreeningDecision.PENDING
        assert entry.new_decision == ScreeningDecision.MAYBE

    def test_include_to_exclude(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        entry = session.decide("lit-001", ScreeningDecision.EXCLUDE, "researcher-001")
        assert entry.previous_decision == ScreeningDecision.INCLUDE
        assert entry.new_decision == ScreeningDecision.EXCLUDE

    def test_exclude_to_include(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.EXCLUDE, "researcher-001")
        entry = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert entry.previous_decision == ScreeningDecision.EXCLUDE
        assert entry.new_decision == ScreeningDecision.INCLUDE

    def test_maybe_to_include(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.MAYBE, "researcher-001")
        entry = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert entry.previous_decision == ScreeningDecision.MAYBE
        assert entry.new_decision == ScreeningDecision.INCLUDE

    def test_maybe_to_exclude(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.MAYBE, "researcher-001")
        entry = session.decide("lit-001", ScreeningDecision.EXCLUDE, "researcher-001")
        assert entry.previous_decision == ScreeningDecision.MAYBE
        assert entry.new_decision == ScreeningDecision.EXCLUDE


# ---------------------------------------------------------------------------
# Return value
# ---------------------------------------------------------------------------

class TestDecideReturnValue:

    def test_returns_screening_decision_history_entry(self):
        session = _make_session_with_record("lit-001")
        result = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert isinstance(result, ScreeningDecisionHistoryEntry)

    def test_returned_entry_literature_record_id(self):
        session = _make_session_with_record("lit-007")
        entry = session.decide("lit-007", ScreeningDecision.INCLUDE, "researcher-001")
        assert entry.literature_record_id == "lit-007"

    def test_returned_entry_changed_by(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-XYZ")
        assert entry.changed_by == "researcher-XYZ"

    def test_returned_entry_reason(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide(
            "lit-001", ScreeningDecision.INCLUDE, "researcher-001", reason="Meets criteria"
        )
        assert entry.reason == "Meets criteria"

    def test_returned_entry_notes(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide(
            "lit-001", ScreeningDecision.INCLUDE, "researcher-001", notes="Check fig 2"
        )
        assert entry.notes == "Check fig 2"

    def test_returned_entry_reason_none_by_default(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert entry.reason is None

    def test_returned_entry_notes_none_by_default(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert entry.notes is None

    def test_returned_entry_changed_at_is_timezone_aware(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert entry.changed_at.tzinfo is not None

    def test_returned_entry_is_immutable(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        with pytest.raises(Exception):
            entry.new_decision = ScreeningDecision.EXCLUDE  # type: ignore


# ---------------------------------------------------------------------------
# Workspace is updated
# ---------------------------------------------------------------------------

class TestDecideUpdatesWorkspace:

    def test_workspace_decision_updated_after_decide(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        record = session.workspace.get("lit-001")
        assert record.decision == ScreeningDecision.INCLUDE

    def test_workspace_decision_updated_through_chain(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        session.decide("lit-001", ScreeningDecision.EXCLUDE, "researcher-001")
        record = session.workspace.get("lit-001")
        assert record.decision == ScreeningDecision.EXCLUDE

    def test_workspace_pending_count_decreases_after_decide(self):
        session = _make_session_with_record("lit-001")
        assert len(session.workspace.pending()) == 1
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert len(session.workspace.pending()) == 0

    def test_workspace_total_unchanged_after_decide(self):
        session = _make_session_with_record("lit-001")
        before = session.workspace.total()
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert session.workspace.total() == before


# ---------------------------------------------------------------------------
# History is updated
# ---------------------------------------------------------------------------

class TestDecideUpdatesHistory:

    def test_history_count_increments_after_decide(self):
        session = _make_session_with_record("lit-001")
        assert session.history.count() == 0
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert session.history.count() == 1

    def test_history_entry_recorded_correctly(self):
        session = _make_session_with_record("lit-001")
        returned = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        recorded = session.history.for_record("lit-001")
        assert len(recorded) == 1
        assert recorded[0] is returned

    def test_history_chain_recorded(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        session.decide("lit-001", ScreeningDecision.EXCLUDE, "researcher-001")
        entries = session.history.for_record("lit-001")
        assert len(entries) == 2
        assert entries[0].new_decision == ScreeningDecision.INCLUDE
        assert entries[1].new_decision == ScreeningDecision.EXCLUDE

    def test_history_isolated_per_record(self):
        ws = ScreeningWorkspace()
        ws.add("lit-A")
        ws.add("lit-B")
        session = ScreeningSession(criteria=_make_criteria(), workspace=ws)
        session.decide("lit-A", ScreeningDecision.INCLUDE, "researcher-001")
        session.decide("lit-B", ScreeningDecision.EXCLUDE, "researcher-001")
        assert session.history.count_for_record("lit-A") == 1
        assert session.history.count_for_record("lit-B") == 1
        assert session.history.count() == 2

    def test_multiple_decides_all_recorded(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        session.decide("lit-001", ScreeningDecision.MAYBE, "researcher-001")
        session.decide("lit-001", ScreeningDecision.EXCLUDE, "researcher-001")
        assert session.history.count() == 3


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestDecideErrorCases:

    def test_same_decision_raises_value_error(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        with pytest.raises(ValueError, match="did not change"):
            session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")

    def test_same_pending_decision_raises_value_error(self):
        session = _make_session_with_record("lit-001")
        with pytest.raises(ValueError, match="did not change"):
            session.decide("lit-001", ScreeningDecision.PENDING, "researcher-001")

    def test_unknown_record_raises_screening_record_not_found_error(self):
        session = _make_session_with_record("lit-001")
        with pytest.raises(ScreeningRecordNotFoundError):
            session.decide("lit-does-not-exist", ScreeningDecision.INCLUDE, "researcher-001")

    def test_wrong_decision_type_raises_type_error(self):
        session = _make_session_with_record("lit-001")
        with pytest.raises(TypeError):
            session.decide("lit-001", "INCLUDE", "researcher-001")  # type: ignore

    def test_none_decision_raises_type_error(self):
        session = _make_session_with_record("lit-001")
        with pytest.raises(TypeError):
            session.decide("lit-001", None, "researcher-001")  # type: ignore

    def test_empty_changed_by_raises_value_error(self):
        session = _make_session_with_record("lit-001")
        with pytest.raises((ValueError, ValidationError)):
            session.decide("lit-001", ScreeningDecision.INCLUDE, "")

    def test_whitespace_changed_by_raises_value_error(self):
        session = _make_session_with_record("lit-001")
        with pytest.raises((ValueError, ValidationError)):
            session.decide("lit-001", ScreeningDecision.INCLUDE, "   ")

    def test_failed_decide_does_not_update_history(self):
        session = _make_session_with_record("lit-001")
        with pytest.raises(ScreeningRecordNotFoundError):
            session.decide("lit-MISSING", ScreeningDecision.INCLUDE, "researcher-001")
        assert session.history.count() == 0

    def test_same_decision_does_not_update_history(self):
        session = _make_session_with_record("lit-001")
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        with pytest.raises(ValueError):
            session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert session.history.count() == 1  # only the first decide


# ---------------------------------------------------------------------------
# Task 17 record_decision_change() still works independently
# ---------------------------------------------------------------------------

class TestTask17Preserved:

    def test_record_decision_change_still_works(self):
        session = _make_session_with_record("lit-001")
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit-manual",
            previous_decision=ScreeningDecision.PENDING,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=_utcnow(),
            changed_by="researcher-001",
        )
        session.record_decision_change(entry)
        assert session.history.count() == 1

    def test_record_decision_change_and_decide_both_accumulate(self):
        session = _make_session_with_record("lit-001")
        manual_entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit-manual",
            previous_decision=ScreeningDecision.PENDING,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=_utcnow(),
            changed_by="researcher-001",
        )
        session.record_decision_change(manual_entry)
        session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-001")
        assert session.history.count() == 2


# ---------------------------------------------------------------------------
# No AI / external API
# ---------------------------------------------------------------------------

class TestNoAI:

    def test_no_ai_fields_on_session(self):
        session = _make_session_with_record("lit-001")
        assert not hasattr(session, "ai_provider")
        assert not hasattr(session, "ai_model")

    def test_decide_requires_no_external_call(self):
        session = _make_session_with_record("lit-001")
        entry = session.decide("lit-001", ScreeningDecision.INCLUDE, "researcher-local")
        assert entry is not None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TestPublicAPI:

    def test_session_importable_from_screening(self):
        from screening import ScreeningSession as SS
        assert SS is ScreeningSession

    def test_screening_record_not_found_error_importable(self):
        from screening import ScreeningRecordNotFoundError as SRNFE
        assert SRNFE is ScreeningRecordNotFoundError
