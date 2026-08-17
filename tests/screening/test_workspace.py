"""Tests for ScreeningWorkspace — fully deterministic and offline."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from domain.actors import ActorType
from domain.screening import ScreeningDecision, ScreeningRecord
from screening.workspace import ScreeningRecordNotFoundError, ScreeningWorkspace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ws(*n_records: int) -> tuple[ScreeningWorkspace, list]:
    """Return a workspace pre-loaded with n unique IDs."""
    count = n_records[0] if n_records else 0
    ws = ScreeningWorkspace()
    ids = [uuid4() for _ in range(count)]
    ws.add_records(ids)
    return ws, ids


def _utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# TEST 19: Initialization
# ---------------------------------------------------------------------------

def test_five_records_all_pending():
    ws, ids = _ws(5)
    c = ws.counts()
    assert ws.total() == 5
    assert c["PENDING"] == 5
    assert c["INCLUDE"] == 0
    assert c["EXCLUDE"] == 0
    assert c["MAYBE"] == 0


def test_initialization_all_records_pending():
    ws, ids = _ws(3)
    for rec in ws.list_records():
        assert rec.decision == ScreeningDecision.PENDING


def test_initialization_decided_at_none():
    ws, ids = _ws(2)
    for rec in ws.list_records():
        assert rec.decided_at is None


def test_initialization_decided_by_none():
    ws, ids = _ws(2)
    for rec in ws.list_records():
        assert rec.decided_by is None


# ---------------------------------------------------------------------------
# TEST 20: Duplicate IDs
# ---------------------------------------------------------------------------

def test_duplicate_id_produces_one_record():
    ws = ScreeningWorkspace()
    lid = uuid4()
    ws.add_record(lid)
    ws.add_record(lid)
    assert ws.total() == 1


def test_duplicate_id_same_record_returned():
    ws = ScreeningWorkspace()
    lid = uuid4()
    r1 = ws.add_record(lid)
    r2 = ws.add_record(lid)
    assert r1.id == r2.id


def test_duplicate_id_list_not_appended():
    ws = ScreeningWorkspace()
    lid = uuid4()
    ws.add_records([lid, lid, lid])
    assert ws.total() == 1


# ---------------------------------------------------------------------------
# TEST 21: GET
# ---------------------------------------------------------------------------

def test_get_existing_record():
    ws, ids = _ws(3)
    rec = ws.get(ids[1])
    assert rec.literature_record_id == ids[1]


def test_get_returns_screening_record():
    ws, ids = _ws(1)
    rec = ws.get(ids[0])
    assert isinstance(rec, ScreeningRecord)


def test_get_preserves_literature_record_id():
    ws = ScreeningWorkspace()
    lid = uuid4()
    ws.add_record(lid)
    assert ws.get(lid).literature_record_id == lid


# ---------------------------------------------------------------------------
# TEST 22: Unknown ID
# ---------------------------------------------------------------------------

def test_get_unknown_id_raises():
    ws, _ = _ws(2)
    with pytest.raises(ScreeningRecordNotFoundError):
        ws.get(uuid4())


def test_set_decision_unknown_id_raises():
    ws, _ = _ws(2)
    with pytest.raises(ScreeningRecordNotFoundError):
        ws.set_decision(uuid4(), ScreeningDecision.INCLUDE, ActorType.RESEARCHER)


def test_not_found_error_carries_id():
    ws = ScreeningWorkspace()
    missing = uuid4()
    with pytest.raises(ScreeningRecordNotFoundError) as exc_info:
        ws.get(missing)
    assert exc_info.value.literature_record_id == missing


# ---------------------------------------------------------------------------
# TEST 23: SET INCLUDE
# ---------------------------------------------------------------------------

def test_set_include_changes_decision():
    ws, ids = _ws(3)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    assert ws.get(ids[0]).decision == ScreeningDecision.INCLUDE


def test_set_include_decreases_pending():
    ws, ids = _ws(3)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    assert ws.counts()["PENDING"] == 2


def test_set_include_increases_include():
    ws, ids = _ws(3)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    assert ws.counts()["INCLUDE"] == 1


def test_set_include_increases_screened_count():
    ws, ids = _ws(3)
    assert ws.screened_count() == 0
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    assert ws.screened_count() == 1


# ---------------------------------------------------------------------------
# TEST 24: SET EXCLUDE
# ---------------------------------------------------------------------------

def test_set_exclude_changes_decision():
    ws, ids = _ws(3)
    ws.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    assert ws.get(ids[1]).decision == ScreeningDecision.EXCLUDE


def test_set_exclude_decreases_pending():
    ws, ids = _ws(3)
    ws.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    assert ws.counts()["PENDING"] == 2


def test_set_exclude_increases_exclude():
    ws, ids = _ws(3)
    ws.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    assert ws.counts()["EXCLUDE"] == 1


def test_set_exclude_with_reason():
    ws, ids = _ws(1)
    ws.set_decision(
        ids[0], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER,
        reason="Wrong intervention."
    )
    assert ws.get(ids[0]).reason == "Wrong intervention."


def test_set_exclude_without_reason():
    ws, ids = _ws(1)
    ws.set_decision(ids[0], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    assert ws.get(ids[0]).reason is None


# ---------------------------------------------------------------------------
# TEST 25: SET MAYBE
# ---------------------------------------------------------------------------

def test_set_maybe_changes_decision():
    ws, ids = _ws(2)
    ws.set_decision(ids[0], ScreeningDecision.MAYBE, ActorType.RESEARCHER)
    assert ws.get(ids[0]).decision == ScreeningDecision.MAYBE


def test_set_maybe_counts():
    ws, ids = _ws(4)
    ws.set_decision(ids[0], ScreeningDecision.MAYBE, ActorType.RESEARCHER)
    c = ws.counts()
    assert c["MAYBE"] == 1
    assert c["PENDING"] == 3


def test_set_maybe_screened():
    ws, ids = _ws(2)
    ws.set_decision(ids[0], ScreeningDecision.MAYBE, ActorType.RESEARCHER)
    assert ws.screened_count() == 1


# ---------------------------------------------------------------------------
# TEST 26: PENDING
# ---------------------------------------------------------------------------

def test_pending_returns_only_pending():
    ws, ids = _ws(4)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    pending = ws.pending()
    assert all(r.decision == ScreeningDecision.PENDING for r in pending)


def test_pending_count_correct():
    ws, ids = _ws(5)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    ws.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    assert len(ws.pending()) == 3


def test_pending_after_all_decided():
    ws, ids = _ws(2)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    ws.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    assert ws.pending() == []


# ---------------------------------------------------------------------------
# TEST 27: COUNTS
# ---------------------------------------------------------------------------

def test_counts_all_four_keys_always_present():
    ws = ScreeningWorkspace()
    c = ws.counts()
    assert "PENDING" in c
    assert "INCLUDE" in c
    assert "EXCLUDE" in c
    assert "MAYBE" in c


def test_counts_zero_values_present():
    ws, ids = _ws(3)
    c = ws.counts()
    assert c["INCLUDE"] == 0
    assert c["EXCLUDE"] == 0
    assert c["MAYBE"] == 0


def test_counts_mixed_decisions():
    ws, ids = _ws(5)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    ws.set_decision(ids[1], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    ws.set_decision(ids[2], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    ws.set_decision(ids[3], ScreeningDecision.MAYBE, ActorType.RESEARCHER)
    c = ws.counts()
    assert c["PENDING"] == 1
    assert c["INCLUDE"] == 2
    assert c["EXCLUDE"] == 1
    assert c["MAYBE"] == 1


def test_counts_empty_workspace():
    ws = ScreeningWorkspace()
    c = ws.counts()
    assert all(v == 0 for v in c.values())


# ---------------------------------------------------------------------------
# TEST 28: PROGRESS
# ---------------------------------------------------------------------------

def test_progress_percentage_two_of_five():
    ws, ids = _ws(5)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    ws.set_decision(ids[1], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    p = ws.progress()
    assert p.total == 5
    assert p.screened == 2
    assert p.pending == 3
    assert abs(p.percentage - 40.0) < 0.001


def test_progress_100_percent():
    ws, ids = _ws(3)
    for lid in ids:
        ws.set_decision(lid, ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    p = ws.progress()
    assert abs(p.percentage - 100.0) < 0.001


def test_progress_zero_percent():
    ws, ids = _ws(3)
    p = ws.progress()
    assert abs(p.percentage - 0.0) < 0.001


# ---------------------------------------------------------------------------
# TEST 29: EMPTY WORKSPACE
# ---------------------------------------------------------------------------

def test_empty_workspace_total_zero():
    ws = ScreeningWorkspace()
    assert ws.total() == 0


def test_empty_workspace_screened_count_zero():
    ws = ScreeningWorkspace()
    assert ws.screened_count() == 0


def test_empty_workspace_pending_empty():
    ws = ScreeningWorkspace()
    assert ws.pending() == []


def test_empty_workspace_progress_no_division_error():
    ws = ScreeningWorkspace()
    p = ws.progress()
    assert p.percentage == 0.0


def test_empty_workspace_list_records_empty():
    ws = ScreeningWorkspace()
    assert ws.list_records() == []


# ---------------------------------------------------------------------------
# TEST 30: ORDER
# ---------------------------------------------------------------------------

def test_list_records_preserves_insertion_order():
    ws = ScreeningWorkspace()
    ids = [uuid4() for _ in range(4)]
    ws.add_records(ids)
    listed = ws.list_records()
    for i, rec in enumerate(listed):
        assert rec.literature_record_id == ids[i]


def test_pending_preserves_insertion_order():
    ws = ScreeningWorkspace()
    ids = [uuid4() for _ in range(4)]
    ws.add_records(ids)
    ws.set_decision(ids[1], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    pending = ws.pending()
    # ids[0], ids[2], ids[3] remain pending in original order
    assert pending[0].literature_record_id == ids[0]
    assert pending[1].literature_record_id == ids[2]
    assert pending[2].literature_record_id == ids[3]


# ---------------------------------------------------------------------------
# TEST 31: RESEARCHER OWNERSHIP
# ---------------------------------------------------------------------------

def test_decided_by_researcher_preserved():
    ws, ids = _ws(1)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    assert ws.get(ids[0]).decided_by == ActorType.RESEARCHER


def test_decided_by_system_preserved():
    ws, ids = _ws(1)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.SYSTEM)
    assert ws.get(ids[0]).decided_by == ActorType.SYSTEM


def test_decided_at_auto_set_utc():
    ws, ids = _ws(1)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    rec = ws.get(ids[0])
    assert rec.decided_at is not None
    assert rec.decided_at.tzinfo is not None


def test_decided_at_custom_preserved():
    ws, ids = _ws(1)
    custom_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    ws.set_decision(
        ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER,
        decided_at=custom_dt
    )
    assert ws.get(ids[0]).decided_at == custom_dt


# ---------------------------------------------------------------------------
# TEST 32: NO AI
# ---------------------------------------------------------------------------

def test_no_ai_imports_in_workspace():
    import inspect
    import screening.workspace as mod
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


def test_workspace_requires_no_external_services():
    ws = ScreeningWorkspace()
    assert ws is not None


# ---------------------------------------------------------------------------
# TEST 33: NO LITERATURE MUTATION
# ---------------------------------------------------------------------------

def test_set_decision_does_not_mutate_literature_record_id():
    ws, ids = _ws(1)
    original_id = ids[0]
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    assert ws.get(original_id).literature_record_id == original_id


# ---------------------------------------------------------------------------
# TEST 34: NO INVENTION
# ---------------------------------------------------------------------------

def test_screening_record_has_no_title():
    ws, ids = _ws(1)
    rec = ws.get(ids[0])
    assert not hasattr(rec, "title")


def test_screening_record_has_no_doi():
    ws, ids = _ws(1)
    rec = ws.get(ids[0])
    assert not hasattr(rec, "doi")


def test_reason_not_invented():
    ws, ids = _ws(1)
    ws.set_decision(ids[0], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    assert ws.get(ids[0]).reason is None


def test_notes_not_invented():
    ws, ids = _ws(1)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    assert ws.get(ids[0]).notes is None


def test_supplied_notes_preserved():
    ws, ids = _ws(1)
    notes = "Needs co-author review."
    ws.set_decision(
        ids[0], ScreeningDecision.MAYBE, ActorType.RESEARCHER, notes=notes
    )
    assert ws.get(ids[0]).notes == notes


# ---------------------------------------------------------------------------
# Changing decision
# ---------------------------------------------------------------------------

def test_decision_can_be_changed():
    ws, ids = _ws(1)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    ws.set_decision(ids[0], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    assert ws.get(ids[0]).decision == ScreeningDecision.EXCLUDE


def test_counts_update_after_decision_change():
    ws, ids = _ws(2)
    ws.set_decision(ids[0], ScreeningDecision.INCLUDE, ActorType.RESEARCHER)
    ws.set_decision(ids[0], ScreeningDecision.EXCLUDE, ActorType.RESEARCHER)
    c = ws.counts()
    assert c["INCLUDE"] == 0
    assert c["EXCLUDE"] == 1


# ---------------------------------------------------------------------------
# Public imports
# ---------------------------------------------------------------------------

def test_screening_workspace_importable():
    from screening import ScreeningWorkspace
    assert ScreeningWorkspace is not None


def test_screening_progress_importable():
    from screening import ScreeningProgress
    assert ScreeningProgress is not None


def test_not_found_error_importable():
    from screening import ScreeningRecordNotFoundError
    assert issubclass(ScreeningRecordNotFoundError, Exception)
