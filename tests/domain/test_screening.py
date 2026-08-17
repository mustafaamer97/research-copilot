"""Tests for the Screening domain contract."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from domain.actors import ActorType
from domain.screening import ScreeningDecision, ScreeningRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _pending(**kwargs) -> ScreeningRecord:
    defaults = dict(literature_record_id=uuid4())
    defaults.update(kwargs)
    return ScreeningRecord(**defaults)


def _final(decision: ScreeningDecision, **kwargs) -> ScreeningRecord:
    defaults = dict(
        literature_record_id=uuid4(),
        decision=decision,
        decided_at=_utc(),
        decided_by=ActorType.RESEARCHER,
    )
    defaults.update(kwargs)
    return ScreeningRecord(**defaults)


# ---------------------------------------------------------------------------
# ScreeningDecision enum
# ---------------------------------------------------------------------------

def test_exact_screening_decisions_exist():
    values = {d.value for d in ScreeningDecision}
    assert values == {"PENDING", "INCLUDE", "EXCLUDE", "MAYBE"}


def test_exactly_four_screening_decisions():
    assert len(ScreeningDecision) == 4


def test_screening_decision_is_str_enum():
    assert isinstance(ScreeningDecision.PENDING, str)
    assert ScreeningDecision.INCLUDE == "INCLUDE"


def test_no_duplicate_decision_type():
    import domain.screening as mod
    for forbidden in ("ScreeningStatus", "ScreeningState", "ScreeningDecisionEnum"):
        assert not hasattr(mod, forbidden)


# ---------------------------------------------------------------------------
# TEST 18: PENDING record
# ---------------------------------------------------------------------------

def test_pending_record_created():
    rec = _pending()
    assert rec.decision == ScreeningDecision.PENDING


def test_pending_decided_at_is_none():
    rec = _pending()
    assert rec.decided_at is None


def test_pending_decided_by_is_none():
    rec = _pending()
    assert rec.decided_by is None


def test_pending_reason_defaults_none():
    rec = _pending()
    assert rec.reason is None


def test_pending_notes_defaults_none():
    rec = _pending()
    assert rec.notes is None


def test_pending_has_id():
    rec = _pending()
    assert rec.id is not None


def test_pending_has_literature_record_id():
    lit_id = uuid4()
    rec = _pending(literature_record_id=lit_id)
    assert rec.literature_record_id == lit_id


# ---------------------------------------------------------------------------
# TEST 19: INCLUDE decision
# ---------------------------------------------------------------------------

def test_include_decision_accepted():
    rec = _final(ScreeningDecision.INCLUDE)
    assert rec.decision == ScreeningDecision.INCLUDE


def test_include_decided_at_preserved():
    dt = _utc()
    rec = _final(ScreeningDecision.INCLUDE, decided_at=dt)
    assert rec.decided_at == dt


def test_include_decided_by_preserved():
    rec = _final(ScreeningDecision.INCLUDE, decided_by=ActorType.RESEARCHER)
    assert rec.decided_by == ActorType.RESEARCHER


def test_include_system_actor_accepted():
    rec = _final(ScreeningDecision.INCLUDE, decided_by=ActorType.SYSTEM)
    assert rec.decided_by == ActorType.SYSTEM


# ---------------------------------------------------------------------------
# TEST 20: EXCLUDE decision
# ---------------------------------------------------------------------------

def test_exclude_decision_accepted():
    rec = _final(ScreeningDecision.EXCLUDE)
    assert rec.decision == ScreeningDecision.EXCLUDE


def test_exclude_with_reason():
    rec = _final(ScreeningDecision.EXCLUDE, reason="Wrong population.")
    assert rec.reason == "Wrong population."


def test_exclude_without_reason():
    rec = _final(ScreeningDecision.EXCLUDE, reason=None)
    assert rec.reason is None


def test_exclude_reason_preserved_exactly():
    reason = "Does not meet inclusion criteria: wrong intervention."
    rec = _final(ScreeningDecision.EXCLUDE, reason=reason)
    assert rec.reason == reason


# ---------------------------------------------------------------------------
# TEST 21: MAYBE decision
# ---------------------------------------------------------------------------

def test_maybe_decision_accepted():
    rec = _final(ScreeningDecision.MAYBE)
    assert rec.decision == ScreeningDecision.MAYBE


def test_maybe_has_decided_at():
    rec = _final(ScreeningDecision.MAYBE)
    assert rec.decided_at is not None


def test_maybe_distinct_from_pending():
    pending = _pending()
    maybe = _final(ScreeningDecision.MAYBE)
    assert pending.decision != maybe.decision


def test_maybe_distinct_from_include():
    assert ScreeningDecision.MAYBE != ScreeningDecision.INCLUDE


def test_maybe_distinct_from_exclude():
    assert ScreeningDecision.MAYBE != ScreeningDecision.EXCLUDE


# ---------------------------------------------------------------------------
# TEST 22: Invalid final decision — missing decided_at
# ---------------------------------------------------------------------------

def test_include_without_decided_at_rejected():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision=ScreeningDecision.INCLUDE,
            decided_at=None,
            decided_by=ActorType.RESEARCHER,
        )


def test_exclude_without_decided_at_rejected():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision=ScreeningDecision.EXCLUDE,
            decided_at=None,
            decided_by=ActorType.RESEARCHER,
        )


def test_maybe_without_decided_at_rejected():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision=ScreeningDecision.MAYBE,
            decided_at=None,
            decided_by=ActorType.RESEARCHER,
        )


def test_include_without_decided_by_rejected():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision=ScreeningDecision.INCLUDE,
            decided_at=_utc(),
            decided_by=None,
        )


def test_exclude_without_decided_by_rejected():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision=ScreeningDecision.EXCLUDE,
            decided_at=_utc(),
            decided_by=None,
        )


def test_maybe_without_decided_by_rejected():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision=ScreeningDecision.MAYBE,
            decided_at=_utc(),
            decided_by=None,
        )


# ---------------------------------------------------------------------------
# TEST 23: Invalid decision value
# ---------------------------------------------------------------------------

def test_unsupported_decision_value_rejected():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision="YES",
        )


def test_numeric_decision_rejected():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision=1,
        )


def test_empty_string_decision_rejected():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision="",
        )


# ---------------------------------------------------------------------------
# TEST 24: Literature record reference only
# ---------------------------------------------------------------------------

def test_screening_record_has_literature_record_id():
    lit_id = uuid4()
    rec = _pending(literature_record_id=lit_id)
    assert rec.literature_record_id == lit_id


def test_screening_record_has_no_title():
    rec = _pending()
    assert not hasattr(rec, "title")


def test_screening_record_has_no_authors():
    rec = _pending()
    assert not hasattr(rec, "authors")


def test_screening_record_has_no_doi():
    rec = _pending()
    assert not hasattr(rec, "doi")


def test_screening_record_has_no_abstract():
    rec = _pending()
    assert not hasattr(rec, "abstract")


def test_screening_record_has_no_journal():
    rec = _pending()
    assert not hasattr(rec, "journal")


# ---------------------------------------------------------------------------
# TEST 25: No AI decision masquerading as researcher decision
# ---------------------------------------------------------------------------

def test_decided_by_is_actor_type():
    rec = _final(ScreeningDecision.INCLUDE)
    assert isinstance(rec.decided_by, ActorType)


def test_ai_actor_does_not_silently_default():
    rec = _pending()
    assert rec.decided_by is None


def test_decision_field_is_screening_decision():
    rec = _pending()
    assert isinstance(rec.decision, ScreeningDecision)


def test_no_separate_ai_recommendation_field_silently_as_decision():
    import domain.screening as mod
    import inspect
    source = inspect.getsource(mod)
    # There must not be a field that silently treats AI output as researcher decision
    assert "ai_decision" not in source.lower() or "ai_recommendation" not in source.lower()


# ---------------------------------------------------------------------------
# TEST 26: UTC timestamps
# ---------------------------------------------------------------------------

def test_final_decision_utc_timestamp_accepted():
    rec = _final(ScreeningDecision.INCLUDE, decided_at=datetime.now(timezone.utc))
    assert rec.decided_at.tzinfo is not None


def test_naive_timestamp_rejected_for_include():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision=ScreeningDecision.INCLUDE,
            decided_at=datetime(2024, 1, 1, 12, 0, 0),  # naive
            decided_by=ActorType.RESEARCHER,
        )


def test_naive_timestamp_rejected_for_exclude():
    with pytest.raises(Exception):
        ScreeningRecord(
            literature_record_id=uuid4(),
            decision=ScreeningDecision.EXCLUDE,
            decided_at=datetime(2024, 6, 15, 9, 0, 0),  # naive
            decided_by=ActorType.RESEARCHER,
        )


def test_non_utc_aware_timestamp_accepted():
    tz = timezone(timedelta(hours=5))
    rec = _final(ScreeningDecision.INCLUDE, decided_at=datetime.now(tz))
    assert rec.decided_at.tzinfo is not None


# ---------------------------------------------------------------------------
# Notes preserved exactly
# ---------------------------------------------------------------------------

def test_notes_preserved_exactly():
    notes = "Needs second reviewer opinion. Check methodology section."
    rec = _final(ScreeningDecision.MAYBE, notes=notes)
    assert rec.notes == notes


def test_notes_default_none():
    rec = _pending()
    assert rec.notes is None


# ---------------------------------------------------------------------------
# Two PENDING records have different IDs
# ---------------------------------------------------------------------------

def test_two_pending_records_have_different_ids():
    r1 = _pending()
    r2 = _pending()
    assert r1.id != r2.id


# ---------------------------------------------------------------------------
# Public imports
# ---------------------------------------------------------------------------

def test_screening_decision_importable_from_domain():
    from domain import ScreeningDecision
    assert ScreeningDecision is not None


def test_screening_record_importable_from_domain():
    from domain import ScreeningRecord
    assert ScreeningRecord is not None


def test_screening_decision_in_domain_all():
    import domain
    assert "ScreeningDecision" in domain.__all__
    assert "ScreeningRecord" in domain.__all__
