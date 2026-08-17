"""Tests for screening decision history."""

import pytest
from datetime import datetime, timezone
from screening.history import ScreeningDecisionHistoryEntry
from screening.decision import ScreeningDecision


class TestScreeningDecisionHistoryEntry:
    """Test ScreeningDecisionHistoryEntry contract."""
    
    def test_pending_to_include_succeeds(self):
        """PENDING → INCLUDE succeeds."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_001",
            previous_decision=ScreeningDecision.PENDING,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_001"
        )
        
        assert entry.literature_record_id == "lit_001"
        assert entry.previous_decision == ScreeningDecision.PENDING
        assert entry.new_decision == ScreeningDecision.INCLUDE
        assert entry.changed_by == "researcher_001"
        assert entry.reason is None
        assert entry.notes is None
    
    def test_include_to_exclude_succeeds(self):
        """INCLUDE → EXCLUDE succeeds."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_002",
            previous_decision=ScreeningDecision.INCLUDE,
            new_decision=ScreeningDecision.EXCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_002"
        )
        
        assert entry.previous_decision == ScreeningDecision.INCLUDE
        assert entry.new_decision == ScreeningDecision.EXCLUDE
    
    def test_exclude_to_include_succeeds(self):
        """EXCLUDE → INCLUDE succeeds."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_003",
            previous_decision=ScreeningDecision.EXCLUDE,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_003"
        )
        
        assert entry.previous_decision == ScreeningDecision.EXCLUDE
        assert entry.new_decision == ScreeningDecision.INCLUDE
    
    def test_include_to_include_fails(self):
        """INCLUDE → INCLUDE fails."""
        with pytest.raises(ValueError, match="Decision did not change"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="lit_004",
                previous_decision=ScreeningDecision.INCLUDE,
                new_decision=ScreeningDecision.INCLUDE,
                changed_at=datetime.now(timezone.utc),
                changed_by="researcher_004"
            )
    
    def test_pending_to_pending_fails(self):
        """PENDING → PENDING fails."""
        with pytest.raises(ValueError, match="Decision did not change"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="lit_005",
                previous_decision=ScreeningDecision.PENDING,
                new_decision=ScreeningDecision.PENDING,
                changed_at=datetime.now(timezone.utc),
                changed_by="researcher_005"
            )
    
    def test_exclude_to_exclude_fails(self):
        """EXCLUDE → EXCLUDE fails."""
        with pytest.raises(ValueError, match="Decision did not change"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="lit_006",
                previous_decision=ScreeningDecision.EXCLUDE,
                new_decision=ScreeningDecision.EXCLUDE,
                changed_at=datetime.now(timezone.utc),
                changed_by="researcher_006"
            )
    
    def test_maybe_to_maybe_fails(self):
        """MAYBE → MAYBE fails."""
        with pytest.raises(ValueError, match="Decision did not change"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="lit_007",
                previous_decision=ScreeningDecision.MAYBE,
                new_decision=ScreeningDecision.MAYBE,
                changed_at=datetime.now(timezone.utc),
                changed_by="researcher_007"
            )
    
    def test_missing_changed_by_fails(self):
        """Missing changed_by fails."""
        with pytest.raises(ValueError, match="Field required"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="lit_008",
                previous_decision=ScreeningDecision.PENDING,
                new_decision=ScreeningDecision.INCLUDE,
                changed_at=datetime.now(timezone.utc)
            )
    
    def test_empty_changed_by_fails(self):
        """Empty changed_by fails."""
        with pytest.raises(ValueError, match="changed_by cannot be empty"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="lit_009",
                previous_decision=ScreeningDecision.PENDING,
                new_decision=ScreeningDecision.INCLUDE,
                changed_at=datetime.now(timezone.utc),
                changed_by=""
            )
    
    def test_whitespace_changed_by_fails(self):
        """Whitespace-only changed_by fails."""
        with pytest.raises(ValueError, match="changed_by cannot be empty"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="lit_010",
                previous_decision=ScreeningDecision.PENDING,
                new_decision=ScreeningDecision.INCLUDE,
                changed_at=datetime.now(timezone.utc),
                changed_by="   "
            )
    
    def test_missing_changed_at_fails(self):
        """Missing changed_at fails."""
        with pytest.raises(ValueError, match="Field required"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="lit_011",
                previous_decision=ScreeningDecision.PENDING,
                new_decision=ScreeningDecision.INCLUDE,
                changed_by="researcher_011"
            )
    
    def test_naive_datetime_fails(self):
        """Naive datetime fails."""
        with pytest.raises(ValueError, match="must be timezone-aware"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="lit_012",
                previous_decision=ScreeningDecision.PENDING,
                new_decision=ScreeningDecision.INCLUDE,
                changed_at=datetime.now(),  # naive
                changed_by="researcher_012"
            )
    
    def test_missing_reason_is_valid(self):
        """Missing reason is valid."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_013",
            previous_decision=ScreeningDecision.PENDING,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_013"
        )
        
        assert entry.reason is None
    
    def test_missing_notes_is_valid(self):
        """Missing notes is valid."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_014",
            previous_decision=ScreeningDecision.PENDING,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_014"
        )
        
        assert entry.notes is None
    
    def test_reason_and_notes_can_be_provided(self):
        """Reason and notes can be provided."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_015",
            previous_decision=ScreeningDecision.INCLUDE,
            new_decision=ScreeningDecision.EXCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_015",
            reason="Does not meet inclusion criteria",
            notes="Wrong population"
        )
        
        assert entry.reason == "Does not meet inclusion criteria"
        assert entry.notes == "Wrong population"
    
    def test_history_entry_is_immutable(self):
        """History entry is immutable."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_016",
            previous_decision=ScreeningDecision.PENDING,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_016"
        )
        
        with pytest.raises(Exception):  # Pydantic frozen model raises ValidationError
            entry.new_decision = ScreeningDecision.EXCLUDE
    
    def test_only_literature_record_id_stored(self):
        """Only literature_record_id is stored, not full LiteratureRecord."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_017",
            previous_decision=ScreeningDecision.PENDING,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_017"
        )
        
        # Verify only ID is stored, not a full record
        assert isinstance(entry.literature_record_id, str)
        assert entry.literature_record_id == "lit_017"
        
        # Verify no other literature fields exist
        assert not hasattr(entry, "title")
        assert not hasattr(entry, "doi")
        assert not hasattr(entry, "pmid")
        assert not hasattr(entry, "abstract")
        assert not hasattr(entry, "authors")
        assert not hasattr(entry, "journal")
    
    def test_empty_literature_record_id_fails(self):
        """Empty literature_record_id fails."""
        with pytest.raises(ValueError, match="literature_record_id cannot be empty"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="",
                previous_decision=ScreeningDecision.PENDING,
                new_decision=ScreeningDecision.INCLUDE,
                changed_at=datetime.now(timezone.utc),
                changed_by="researcher_018"
            )
    
    def test_whitespace_literature_record_id_fails(self):
        """Whitespace-only literature_record_id fails."""
        with pytest.raises(ValueError, match="literature_record_id cannot be empty"):
            ScreeningDecisionHistoryEntry(
                literature_record_id="   ",
                previous_decision=ScreeningDecision.PENDING,
                new_decision=ScreeningDecision.INCLUDE,
                changed_at=datetime.now(timezone.utc),
                changed_by="researcher_019"
            )
    
    def test_no_ai_provider_or_external_api_required(self):
        """No AI/provider/external API is required."""
        # Creating a history entry is purely deterministic
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_020",
            previous_decision=ScreeningDecision.MAYBE,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_020"
        )
        
        # No AI fields exist
        assert not hasattr(entry, "ai_provider")
        assert not hasattr(entry, "ai_model")
        assert not hasattr(entry, "ai_confidence")
        assert not hasattr(entry, "ai_reasoning")
    
    def test_pending_to_maybe_succeeds(self):
        """PENDING → MAYBE succeeds."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_021",
            previous_decision=ScreeningDecision.PENDING,
            new_decision=ScreeningDecision.MAYBE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_021"
        )
        
        assert entry.previous_decision == ScreeningDecision.PENDING
        assert entry.new_decision == ScreeningDecision.MAYBE
    
    def test_maybe_to_include_succeeds(self):
        """MAYBE → INCLUDE succeeds."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_022",
            previous_decision=ScreeningDecision.MAYBE,
            new_decision=ScreeningDecision.INCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_022"
        )
        
        assert entry.previous_decision == ScreeningDecision.MAYBE
        assert entry.new_decision == ScreeningDecision.INCLUDE
    
    def test_maybe_to_exclude_succeeds(self):
        """MAYBE → EXCLUDE succeeds."""
        entry = ScreeningDecisionHistoryEntry(
            literature_record_id="lit_023",
            previous_decision=ScreeningDecision.MAYBE,
            new_decision=ScreeningDecision.EXCLUDE,
            changed_at=datetime.now(timezone.utc),
            changed_by="researcher_023"
        )
        
        assert entry.previous_decision == ScreeningDecision.MAYBE
        assert entry.new_decision == ScreeningDecision.EXCLUDE
