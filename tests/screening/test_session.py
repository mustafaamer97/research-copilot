"""Tests for ScreeningSession — fully deterministic and offline."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from domain.actors import ActorType
from domain.screening import ScreeningDecision, ScreeningRecord
from screening.criteria import ExclusionCriteria, InclusionCriteria, ScreeningCriteria
from screening.session import ScreeningSession
from screening.workspace import ScreeningRecordNotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _criteria() -> ScreeningCriteria:
    return ScreeningCriteria(
        inclusion_criteria=InclusionCriteria(
            description="RCTs in adults with type 2 diabetes."
        ),
        exclusion_criteria=ExclusionCriteria(
            description="Animal studies, case reports, editorials."
        ),
    )


def _session(n: int = 0, **kwargs) -> tuple[ScreeningSession, list]:
    ids = [uuid4() for _ in range(n)]
    sess = ScreeningSession(
        criteria=_criteria(),
        literature_record_ids=ids,
        **kwargs,
    )
    return sess, ids


# ---------------------------------------------------------------------------
# TEST 14: Valid session
# ---------------------------------------------------------------------------

def test_valid_session_created():
    sess, ids = _session(3)
    assert sess is not None


def test_session_has_stable_id():
    sess, _ = _session(2)
    assert sess.id is not None


def test_session_id_is_uuid():
    from uuid import UUID
    sess, _ = _session()
    assert isinstance(sess.id, UUID)


def test_session_id_stable_across_accesses():
    sess, _ = _session(1)
    assert sess.id == sess.id


def test_two_sessions_have_different_ids():
    s1, _ = _session(1)
    s2, _ = _session(1)
    assert s1.id != s2.id


def test_session_criteria_present():
    sess, _ = _session(2)
    assert sess.criteria is not None


def test_session_workspace_exists():
    sess, _ = _session(2)
    assert sess.workspace is not None


def test_session_total_correct():
    sess, ids = _session(4)
    assert sess.total() == 4


def test_session_all_records_pending():
    sess, ids = _session(3)
    for rec in sess.workspace.list_records():
        assert rec.decision == ScreeningDecision.PENDING


# ---------------------------------------------------------------------------
# TEST 15: Empty session
# ---------------------------------------------------------------------------

def test_empty_session_total_zero():
    sess, _ = _session(0)
    assert sess.total() == 0


def test_empty_session_pending_empty():
    sess, _ = _session(0)
    assert sess.pending() == []


def test_empty_session_progress_zero_percent():
    sess, _ = _session(0)
    p = sess.progress()
    assert p.percentage == 0.0


def test_empty_session_no_division_error():
    sess, _ = _session(0)
    p = sess.progress()
    assert p is not None


def test_empty_session_counts_all_zero():
    sess, _ = _session(0)
    c = sess.counts()
    assert all(v == 0 for v in c.values())


# ---------------------------------------------------------------------------
# TEST 16: Duplicate literature IDs
# ---------------------------------------------------------------------------

def test_duplicate_ids_produce_one_record():
    lit_id = uuid4()
    sess = ScreeningSession(
        criteria=_criteria(),
        literature_record_ids=[lit_id, lit_id, lit_id],
    )
    assert sess.total() == 1


def test_duplicate_ids_one_pending_record():
    lit_id = uuid4()
    sess = ScreeningSession(
        criteria=_criteria(),
        literature_record_ids=[lit_id, lit_id],
    )
    assert len(sess.pending()) == 1


# ---------------------------------------------------------------------------
# TEST 17: GET delegation
# ---------------------------------------------------------------------------

def test_get_delegates_to_workspace():
    sess, ids = _session(3)
    rec = sess.get_screening_record(ids[1])
    assert isinstance(rec, ScreeningRecord)
    assert rec.literature_record_id == ids[1]


def test_get_unknown_id_raises():
    sess, _ = _session(2)
    with pytest.raises(ScreeningRecordNotFoundError):
        sess.get_screening_record(uuid4())


def test_get_result_matches_workspace():
    sess, ids = _session(2)
    via_session = sess.get_screening_record(ids[0])
    via_workspace = sess.workspace.get(ids[0])
    assert via_session.id == via_workspace.id


# ---------------------------------------------------------------------------
# TEST 18: DECISION delegation
# ---------------------------------------------------------------------------

def test_set_decision_delegates_to_workspace():
    sess, ids = _session(3)
    sess.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    rec = sess.get_screening_record(ids[0])
    assert rec.decision == ScreeningDecision.INCLUDE


def test_set_decision_updates_workspace():
    sess, ids = _session(2)
    sess.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    assert sess.workspace.get(ids[1]).decision == ScreeningDecision.EXCLUDE


def test_set_decision_returns_screening_record():
    sess, ids = _session(1)
    result = sess.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    assert isinstance(result, ScreeningRecord)


def test_set_decision_with_reason():
    sess, ids = _session(1)
    sess.set_decision(
        ids[0], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER,
        reason="Wrong study design."
    )
    assert sess.get_screening_record(ids[0]).reason == "Wrong study design."


def test_set_decision_with_notes():
    sess, ids = _session(1)
    sess.set_decision(
        ids[0], ScreeningDecision.MAYBE, ActorType.RESEARCHER,
        notes="Requires second review."
    )
    assert sess.get_screening_record(ids[0]).notes == "Requires second review."


# ---------------------------------------------------------------------------
# TEST 19: COUNTS delegation
# ---------------------------------------------------------------------------

def test_counts_delegation_matches_workspace():
    sess, ids = _session(4)
    sess.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    sess.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    session_counts = sess.counts()
    workspace_counts = sess.workspace.counts()
    assert session_counts == workspace_counts


def test_counts_all_four_keys_present():
    sess, _ = _session(3)
    c = sess.counts()
    assert "PENDING" in c
    assert "INCLUDE" in c
    assert "EXCLUDE" in c
    assert "MAYBE" in c


def test_counts_correct_after_decisions():
    sess, ids = _session(5)
    sess.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    sess.set_decision(ids[1], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    sess.set_decision(ids[2], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    sess.set_decision(ids[3], ScreeningDecision.MAYBE, ActorType.RESEARCHER)
    c = sess.counts()
    assert c["PENDING"] == 1
    assert c["INCLUDE"] == 2
    assert c["EXCLUDE"] == 1
    assert c["MAYBE"] == 1


# ---------------------------------------------------------------------------
# TEST 20: PROGRESS delegation
# ---------------------------------------------------------------------------

def test_progress_delegates_to_workspace():
    sess, ids = _session(5)
    sess.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    sess.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    p = sess.progress()
    wp = sess.workspace.progress()
    assert p.total == wp.total
    assert p.screened == wp.screened
    assert p.pending == wp.pending
    assert abs(p.percentage - wp.percentage) < 0.001


def test_progress_percentage_correct():
    sess, ids = _session(5)
    sess.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    sess.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    p = sess.progress()
    assert abs(p.percentage - 40.0) < 0.001


# ---------------------------------------------------------------------------
# TEST 21: PENDING delegation
# ---------------------------------------------------------------------------

def test_pending_delegates_to_workspace():
    sess, ids = _session(4)
    sess.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    session_pending = sess.pending()
    workspace_pending = sess.workspace.pending()
    assert len(session_pending) == len(workspace_pending)
    for sp, wp in zip(session_pending, workspace_pending):
        assert sp.id == wp.id


def test_pending_all_pending_decision():
    sess, ids = _session(3)
    sess.set_decision(ids[2], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    for rec in sess.pending():
        assert rec.decision == ScreeningDecision.PENDING


# ---------------------------------------------------------------------------
# TEST 22: Criteria required
# ---------------------------------------------------------------------------

def test_session_without_criteria_raises():
    with pytest.raises(Exception):
        ScreeningSession(criteria=None, literature_record_ids=[])


def test_session_requires_valid_criteria_type():
    with pytest.raises(Exception):
        ScreeningSession(criteria="not criteria", literature_record_ids=[])


# ---------------------------------------------------------------------------
# TEST 23: No criteria mutation method
# ---------------------------------------------------------------------------

def test_no_update_criteria_method():
    sess, _ = _session()
    assert not callable(getattr(sess, "update_criteria", None))


def test_no_set_criteria_method():
    sess, _ = _session()
    assert not callable(getattr(sess, "set_criteria", None))


def test_criteria_property_preserved():
    c = _criteria()
    sess = ScreeningSession(criteria=c, literature_record_ids=[])
    assert sess.criteria is c


def test_criteria_inclusion_preserved():
    sess, _ = _session()
    assert sess.criteria.inclusion_criteria.description == "RCTs in adults with type 2 diabetes."


def test_criteria_exclusion_preserved():
    sess, _ = _session()
    assert sess.criteria.exclusion_criteria.description == "Animal studies, case reports, editorials."


# ---------------------------------------------------------------------------
# TEST 24: No literature mutation
# ---------------------------------------------------------------------------

def test_set_decision_does_not_mutate_literature_id():
    sess, ids = _session(2)
    original = ids[0]
    sess.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    assert sess.get_screening_record(original).literature_record_id == original


# ---------------------------------------------------------------------------
# TEST 25: No AI
# ---------------------------------------------------------------------------

def test_no_ai_imports_in_session_module():
    import inspect
    import screening.session as mod
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


def test_no_http_in_session_module():
    import inspect
    import screening.session as mod
    source = inspect.getsource(mod)
    assert "urllib.request.urlopen" not in source
    assert "requests" not in source


def test_session_construction_requires_no_external_service():
    sess, _ = _session(2)
    assert sess is not None


# ---------------------------------------------------------------------------
# Session ID can be supplied explicitly
# ---------------------------------------------------------------------------

def test_explicit_session_id_preserved():
    fixed_id = uuid4()
    sess = ScreeningSession(criteria=_criteria(), session_id=fixed_id)
    assert sess.id == fixed_id


# ---------------------------------------------------------------------------
# Public imports
# ---------------------------------------------------------------------------

def test_screening_session_importable():
    from screening import ScreeningSession
    assert ScreeningSession is not None


def test_screening_session_in_all():
    import screening
    assert "ScreeningSession" in screening.__all__
