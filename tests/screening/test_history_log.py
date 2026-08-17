"""
Tests for ScreeningHistory — Task 16.

ScreeningHistory is an append-only log of ScreeningDecisionHistoryEntry objects.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from pydantic import ValidationError

from screening.decision import ScreeningDecision
from screening.history import ScreeningDecisionHistoryEntry, ScreeningHistory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _entry(
    record_id: str = "lit-001",
    previous: ScreeningDecision = ScreeningDecision.PENDING,
    new: ScreeningDecision = ScreeningDecision.INCLUDE,
    changed_by: str = "researcher-001",
    reason: str | None = None,
    notes: str | None = None,
) -> ScreeningDecisionHistoryEntry:
    return ScreeningDecisionHistoryEntry(
        literature_record_id=record_id,
        previous_decision=previous,
        new_decision=new,
        changed_at=_utcnow(),
        changed_by=changed_by,
        reason=reason,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestScreeningHistoryConstruction:

    def test_empty_on_creation(self):
        history = ScreeningHistory()
        assert history.count() == 0

    def test_all_entries_empty_on_creation(self):
        history = ScreeningHistory()
        assert history.all_entries() == []

    def test_importable_from_screening_package(self):
        from screening import ScreeningHistory as SH
        assert SH is ScreeningHistory


# ---------------------------------------------------------------------------
# record()
# ---------------------------------------------------------------------------

class TestScreeningHistoryRecord:

    def test_record_single_entry(self):
        history = ScreeningHistory()
        history.record(_entry())
        assert history.count() == 1

    def test_record_multiple_entries(self):
        history = ScreeningHistory()
        history.record(_entry(record_id="lit-001"))
        history.record(_entry(record_id="lit-002"))
        history.record(_entry(record_id="lit-003"))
        assert history.count() == 3

    def test_record_multiple_entries_same_record(self):
        history = ScreeningHistory()
        history.record(_entry(
            record_id="lit-001",
            previous=ScreeningDecision.PENDING,
            new=ScreeningDecision.INCLUDE,
        ))
        history.record(_entry(
            record_id="lit-001",
            previous=ScreeningDecision.INCLUDE,
            new=ScreeningDecision.EXCLUDE,
        ))
        assert history.count() == 2
        assert history.count_for_record("lit-001") == 2

    def test_record_rejects_non_entry_type(self):
        history = ScreeningHistory()
        with pytest.raises(TypeError):
            history.record("not an entry")  # type: ignore

    def test_record_rejects_none(self):
        history = ScreeningHistory()
        with pytest.raises(TypeError):
            history.record(None)  # type: ignore

    def test_record_rejects_dict(self):
        history = ScreeningHistory()
        with pytest.raises(TypeError):
            history.record({  # type: ignore
                "literature_record_id": "lit-001",
                "previous_decision": ScreeningDecision.PENDING,
                "new_decision": ScreeningDecision.INCLUDE,
            })

    def test_record_preserves_insertion_order(self):
        history = ScreeningHistory()
        e1 = _entry(record_id="lit-001", previous=ScreeningDecision.PENDING, new=ScreeningDecision.INCLUDE)
        e2 = _entry(record_id="lit-001", previous=ScreeningDecision.INCLUDE, new=ScreeningDecision.EXCLUDE)
        e3 = _entry(record_id="lit-001", previous=ScreeningDecision.EXCLUDE, new=ScreeningDecision.MAYBE)
        history.record(e1)
        history.record(e2)
        history.record(e3)
        entries = history.for_record("lit-001")
        assert entries[0] is e1
        assert entries[1] is e2
        assert entries[2] is e3


# ---------------------------------------------------------------------------
# for_record()
# ---------------------------------------------------------------------------

class TestScreeningHistoryForRecord:

    def test_for_record_returns_entries_for_id(self):
        history = ScreeningHistory()
        e = _entry(record_id="lit-001")
        history.record(e)
        result = history.for_record("lit-001")
        assert len(result) == 1
        assert result[0] is e

    def test_for_record_returns_empty_list_for_unknown_id(self):
        history = ScreeningHistory()
        assert history.for_record("unknown-record") == []

    def test_for_record_isolates_by_id(self):
        history = ScreeningHistory()
        e1 = _entry(record_id="lit-001")
        e2 = _entry(record_id="lit-002")
        history.record(e1)
        history.record(e2)
        assert history.for_record("lit-001") == [e1]
        assert history.for_record("lit-002") == [e2]

    def test_for_record_returns_copy_not_internal_list(self):
        history = ScreeningHistory()
        history.record(_entry(record_id="lit-001"))
        result = history.for_record("lit-001")
        result.clear()
        assert history.count_for_record("lit-001") == 1

    def test_for_record_in_insertion_order(self):
        history = ScreeningHistory()
        e1 = _entry(record_id="lit-A", previous=ScreeningDecision.PENDING, new=ScreeningDecision.INCLUDE)
        e2 = _entry(record_id="lit-A", previous=ScreeningDecision.INCLUDE, new=ScreeningDecision.EXCLUDE)
        history.record(e1)
        history.record(e2)
        entries = history.for_record("lit-A")
        assert entries[0].new_decision == ScreeningDecision.INCLUDE
        assert entries[1].new_decision == ScreeningDecision.EXCLUDE


# ---------------------------------------------------------------------------
# all_entries()
# ---------------------------------------------------------------------------

class TestScreeningHistoryAllEntries:

    def test_all_entries_returns_all_in_insertion_order(self):
        history = ScreeningHistory()
        e1 = _entry(record_id="lit-001")
        e2 = _entry(record_id="lit-002")
        e3 = _entry(record_id="lit-001", previous=ScreeningDecision.INCLUDE, new=ScreeningDecision.EXCLUDE)
        history.record(e1)
        history.record(e2)
        history.record(e3)
        result = history.all_entries()
        assert result == [e1, e2, e3]

    def test_all_entries_returns_copy(self):
        history = ScreeningHistory()
        history.record(_entry())
        result = history.all_entries()
        result.clear()
        assert history.count() == 1

    def test_all_entries_empty_when_no_records(self):
        history = ScreeningHistory()
        assert history.all_entries() == []


# ---------------------------------------------------------------------------
# count() and count_for_record()
# ---------------------------------------------------------------------------

class TestScreeningHistoryCounts:

    def test_count_zero_initially(self):
        assert ScreeningHistory().count() == 0

    def test_count_increments_on_record(self):
        history = ScreeningHistory()
        history.record(_entry(record_id="lit-001"))
        assert history.count() == 1
        history.record(_entry(record_id="lit-002"))
        assert history.count() == 2

    def test_count_for_record_zero_for_unknown(self):
        assert ScreeningHistory().count_for_record("nobody") == 0

    def test_count_for_record_correct(self):
        history = ScreeningHistory()
        history.record(_entry(record_id="lit-X"))
        history.record(_entry(record_id="lit-X", previous=ScreeningDecision.INCLUDE, new=ScreeningDecision.EXCLUDE))
        history.record(_entry(record_id="lit-Y"))
        assert history.count_for_record("lit-X") == 2
        assert history.count_for_record("lit-Y") == 1


# ---------------------------------------------------------------------------
# has_history()
# ---------------------------------------------------------------------------

class TestScreeningHistoryHasHistory:

    def test_has_history_false_for_unknown(self):
        assert ScreeningHistory().has_history("unknown") is False

    def test_has_history_true_after_record(self):
        history = ScreeningHistory()
        history.record(_entry(record_id="lit-001"))
        assert history.has_history("lit-001") is True

    def test_has_history_false_for_different_id(self):
        history = ScreeningHistory()
        history.record(_entry(record_id="lit-001"))
        assert history.has_history("lit-002") is False


# ---------------------------------------------------------------------------
# No mutation of stored entries
# ---------------------------------------------------------------------------

class TestScreeningHistoryEntryImmutability:

    def test_stored_entries_are_immutable(self):
        history = ScreeningHistory()
        e = _entry()
        history.record(e)
        retrieved = history.all_entries()[0]
        with pytest.raises(Exception):
            retrieved.new_decision = ScreeningDecision.EXCLUDE  # type: ignore

    def test_stored_entries_identical_objects(self):
        history = ScreeningHistory()
        e = _entry()
        history.record(e)
        assert history.all_entries()[0] is e


# ---------------------------------------------------------------------------
# No AI / external API
# ---------------------------------------------------------------------------

class TestScreeningHistoryNoAI:

    def test_no_ai_provider_field(self):
        history = ScreeningHistory()
        assert not hasattr(history, "ai_provider")

    def test_no_external_api_needed(self):
        history = ScreeningHistory()
        e = _entry()
        history.record(e)
        assert history.count() == 1

    def test_multiple_records_multiple_decisions_no_ai(self):
        history = ScreeningHistory()
        for i in range(10):
            history.record(_entry(record_id=f"lit-{i:03d}"))
        assert history.count() == 10


# ---------------------------------------------------------------------------
# No ScreeningWorkspace modification required
# ---------------------------------------------------------------------------

class TestScreeningHistoryIndependence:

    def test_history_is_independent_of_workspace(self):
        """ScreeningHistory does not require ScreeningWorkspace to function."""
        history = ScreeningHistory()
        history.record(_entry())
        assert history.count() == 1

    def test_history_does_not_import_workspace(self):
        """Verify no circular or workspace dependency at import time."""
        import screening.history as h
        assert not hasattr(h, "ScreeningWorkspace")


# ---------------------------------------------------------------------------
# Audit trail scenario
# ---------------------------------------------------------------------------

class TestScreeningHistoryAuditTrail:

    def test_full_decision_chain_for_one_record(self):
        """
        Simulate: PENDING → INCLUDE → EXCLUDE → INCLUDE
        Three explicit changes produce three history entries.
        """
        history = ScreeningHistory()
        rid = "lit-audit-001"

        history.record(_entry(rid, ScreeningDecision.PENDING, ScreeningDecision.INCLUDE))
        history.record(_entry(rid, ScreeningDecision.INCLUDE, ScreeningDecision.EXCLUDE))
        history.record(_entry(rid, ScreeningDecision.EXCLUDE, ScreeningDecision.INCLUDE))

        entries = history.for_record(rid)
        assert len(entries) == 3
        assert entries[0].previous_decision == ScreeningDecision.PENDING
        assert entries[0].new_decision == ScreeningDecision.INCLUDE
        assert entries[1].previous_decision == ScreeningDecision.INCLUDE
        assert entries[1].new_decision == ScreeningDecision.EXCLUDE
        assert entries[2].previous_decision == ScreeningDecision.EXCLUDE
        assert entries[2].new_decision == ScreeningDecision.INCLUDE

    def test_multiple_records_independent_histories(self):
        history = ScreeningHistory()

        history.record(_entry("rec-A", ScreeningDecision.PENDING, ScreeningDecision.INCLUDE))
        history.record(_entry("rec-B", ScreeningDecision.PENDING, ScreeningDecision.EXCLUDE))
        history.record(_entry("rec-A", ScreeningDecision.INCLUDE, ScreeningDecision.MAYBE))

        assert history.count_for_record("rec-A") == 2
        assert history.count_for_record("rec-B") == 1
        assert history.count() == 3

    def test_initial_pending_not_recorded(self):
        """
        Initial PENDING state of a ScreeningRecord does not produce a history entry.
        If a researcher never changes the decision, history remains empty.
        """
        history = ScreeningHistory()
        assert history.has_history("lit-never-decided") is False
        assert history.count() == 0
