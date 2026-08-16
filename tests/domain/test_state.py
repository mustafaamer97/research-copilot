"""Tests for ResearchState."""
import pytest
from domain.state import ResearchState


EXPECTED_STATES = [
    "IDEA",
    "QUESTION_DEFINED",
    "FRAMEWORK_DEFINED",
    "DESIGN_SELECTED",
    "PROTOCOL_READY",
    "LITERATURE_SEARCH",
    "SCREENING",
    "DATA_COLLECTION",
    "DATA_READY",
    "ANALYSIS_PLAN_LOCKED",
    "ANALYSIS_COMPLETE",
    "MANUSCRIPT_DRAFT",
    "AUDIT",
    "JOURNAL_SELECTION",
    "READY_FOR_SUBMISSION",
]


def test_exact_states_exist():
    values = [s.value for s in ResearchState]
    assert values == EXPECTED_STATES


def test_state_count():
    assert len(ResearchState) == 15


def test_no_duplicate_values():
    values = [s.value for s in ResearchState]
    assert len(values) == len(set(values))


def test_no_alternate_lifecycle_enums():
    import domain.state as state_module
    names = dir(state_module)
    for forbidden in ("ProjectState", "ResearchStateEnum", "ResearchStatus", "ProjectStatus"):
        assert forbidden not in names


def test_research_state_is_str_enum():
    assert isinstance(ResearchState.IDEA, str)
    assert ResearchState.IDEA == "IDEA"
