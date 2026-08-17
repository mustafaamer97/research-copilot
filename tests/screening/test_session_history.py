"""
Tests for ScreeningSession history integration — Task 17.

ScreeningSession now owns a ScreeningHistory and exposes:
- session.history  → ScreeningHistory instance
- session.record_decision_change(entry)  → records into history

Rules verified:
- session.history is a ScreeningHistory
- history starts empty
- record_decision_change() stores entries
- entries are retrievable via session.history
- wrong type is rejected
- history is independent per session
- no AI, no external API
- workspace is NOT modified by record_decision_change()
- existing session behaviour (session_id, criteria, workspace) is preserved
"""

from __future__ import annotations

import pytest
import uuid
from datetime import datetime, timezone

from pydantic import ValidationError

from screening.criteria import ScreeningCriteria, InclusionCriteria, ExclusionCriteria
from screening.decision import ScreeningDecision
from screening.history import ScreeningDecisionHistoryEntry, ScreeningHistory
from screening.session import ScreeningSession
from screening.workspace import ScreeningWorkspace


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


def _make_workspace() -> ScreeningWorkspace:
    return ScreeningWorkspace()


def _make_session(
    criteria: ScreeningCriteria | None = None,
    workspace: ScreeningWorkspace | None = None,
    session_id: str | None = None,
) -> ScreeningSession:
    return ScreeningSession(
        criteria=criteria or _make_criteria(),
        workspace=workspace or _make_workspace(),
        session_id=session_id,
    )


def _make_entry(
    record_id: str = "lit-001",
    previous: ScreeningDecision = ScreeningDecision.PENDING,
    new: ScreeningDecision = ScreeningDecision.INCLUDE,
    changed_by: str = "researcher-001",
) -> ScreeningDecisionHistoryEntry:
    return ScreeningDecisionHistoryEntry(
        literature_record_id=record_id,
        previous_decision=previous,
        new_decision=new,
        changed_at=_utcnow(),
        changed_by=changed_by,
    )


# ---------------------------------------------------------------------------
# session.history property
# ---------------------------------------------------------------------------

class TestSessionHistoryProperty:

    def test_history_property_exists(self):
        session = _make_session()
        assert hasattr(session, "history")

    def test_history_is_screening_history_instance(self):
        session = _make_session()
        assert isinstance(session.history, ScreeningHistory)

    def test_history_starts_empty(self):
        session = _make_session()
        assert session.history.count() == 0
        assert session.history.all_entries() == []

    def test_history_property_returns_same_instance(self):
        session = _make_session()
        h1 = session.history
        h2 = session.history
        assert h1 is h2

    def test_each_session_has_independent_history(self):
        s1 = _make_session()
        s2 = _make_session()
        s1.record_decision_change(_make_entry())
        assert s1.history.count() == 1
        assert s2.history.count() == 0


# ---------------------------------------------------------------------------
# record_decision_change()
# ---------------------------------------------------------------------------

class TestRecordDecisionChange:

    def test_record_single_entry(self):
        session = _make_session()
        entry = _make_entry()
        session.record_decision_change(entry)
        assert session.history.count() == 1

    def test_record_entry_is_retrievable(self):
        session = _make_session()
        entry = _make_entry(record_id="lit-X")
        session.record_decision_change(entry)
        result = session.history.for_record("lit-X")
        assert len(result) == 1
        assert result[0] is entry

    def test_record_multiple_entries(self):
        session = _make_session()
        e1 = _make_entry(record_id="lit-001")
        e2 = _make_entry(record_id="lit-002")
        e3 = _make_entry(
            record_id="lit-001",
            previous=ScreeningDecision.INCLUDE,
            new=ScreeningDecision.EXCLUDE,
        )
        session.record_decision_change(e1)
        session.record_decision_change(e2)
        session.record_decision_change(e3)
        assert session.history.count() == 3
        assert session.history.count_for_record("lit-001") == 2
        assert session.history.count_for_record("lit-002") == 1

    def test_record_preserves_insertion_order(self):
        session = _make_session()
        e1 = _make_entry(record_id="lit-A", previous=ScreeningDecision.PENDING, new=ScreeningDecision.INCLUDE)
        e2 = _make_entry(record_id="lit-A", previous=ScreeningDecision.INCLUDE, new=ScreeningDecision.EXCLUDE)
        session.record_decision_change(e1)
        session.record_decision_change(e2)
        entries = session.history.for_record("lit-A")
        assert entries[0] is e1
        assert entries[1] is e2

    def test_record_wrong_type_raises_type_error(self):
        session = _make_session()
        with pytest.raises(TypeError):
            session.record_decision_change("not an entry")  # type: ignore

    def test_record_none_raises_type_error(self):
        session = _make_session()
        with pytest.raises(TypeError):
            session.record_decision_change(None)  # type: ignore

    def test_record_dict_raises_type_error(self):
        session = _make_session()
        with pytest.raises(TypeError):
            session.record_decision_change({  # type: ignore
                "literature_record_id": "lit-001",
                "previous_decision": ScreeningDecision.PENDING,
                "new_decision": ScreeningDecision.INCLUDE,
            })

    def test_record_does_not_modify_workspace(self):
        workspace = _make_workspace()
        session = _make_session(workspace=workspace)
        initial_total = workspace.total()
        entry = _make_entry()
        session.record_decision_change(entry)
        assert workspace.total() == initial_total

    def test_record_does_not_call_set_decision_on_workspace(self):
        """
        record_decision_change is history-only.
        Workspace decision state is unchanged.
        """
        workspace = _make_workspace()
        session = _make_session(workspace=workspace)
        entry = _make_entry(record_id="lit-not-in-workspace")
        # This must not raise even though lit-not-in-workspace is not in workspace
        session.record_decision_change(entry)
        assert session.history.count() == 1


# ---------------------------------------------------------------------------
# Existing session behaviour preserved
# ---------------------------------------------------------------------------

class TestExistingSessionBehaviourPreserved:

    def test_session_id_is_string(self):
        session = _make_session()
        assert isinstance(session.session_id, str)

    def test_session_id_stable(self):
        session = _make_session(session_id="fixed-id-001")
        assert session.session_id == "fixed-id-001"

    def test_session_id_auto_generated_when_not_provided(self):
        session = _make_session()
        assert len(session.session_id) > 0
        # Should be a valid UUID
        uuid.UUID(session.session_id)

    def test_criteria_accessible(self):
        criteria = _make_criteria()
        session = _make_session(criteria=criteria)
        assert session.criteria is criteria

    def test_workspace_accessible(self):
        workspace = _make_workspace()
        session = _make_session(workspace=workspace)
        assert session.workspace is workspace

    def test_wrong_criteria_type_raises(self):
        with pytest.raises(TypeError):
            ScreeningSession(
                criteria="not criteria",  # type: ignore
                workspace=_make_workspace(),
            )

    def test_wrong_workspace_type_raises(self):
        with pytest.raises(TypeError):
            ScreeningSession(
                criteria=_make_criteria(),
                workspace="not workspace",  # type: ignore
            )


# ---------------------------------------------------------------------------
# No AI / external API
# ---------------------------------------------------------------------------

class TestNoAI:

    def test_no_ai_provider_field(self):
        session = _make_session()
        assert not hasattr(session, "ai_provider")

    def test_session_created_without_external_dependency(self):
        session = _make_session()
        entry = _make_entry()
        session.record_decision_change(entry)
        assert session.history.count() == 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TestPublicAPI:

    def test_session_importable_from_screening(self):
        from screening import ScreeningSession as SS
        assert SS is ScreeningSession

    def test_history_importable_from_screening(self):
        from screening import ScreeningHistory as SH
        assert SH is ScreeningHistory

    def test_history_entry_importable_from_screening(self):
        from screening import ScreeningDecisionHistoryEntry as SDHE
        assert SDHE is ScreeningDecisionHistoryEntry
