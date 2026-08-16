"""Tests for canonical transition graph."""
import pytest
from domain.state import ResearchState
from state_machine.transitions import ALLOWED_TRANSITIONS, is_transition_allowed

_ORDERED = [
    ResearchState.IDEA,
    ResearchState.QUESTION_DEFINED,
    ResearchState.FRAMEWORK_DEFINED,
    ResearchState.DESIGN_SELECTED,
    ResearchState.PROTOCOL_READY,
    ResearchState.LITERATURE_SEARCH,
    ResearchState.SCREENING,
    ResearchState.DATA_COLLECTION,
    ResearchState.DATA_READY,
    ResearchState.ANALYSIS_PLAN_LOCKED,
    ResearchState.ANALYSIS_COMPLETE,
    ResearchState.MANUSCRIPT_DRAFT,
    ResearchState.AUDIT,
    ResearchState.JOURNAL_SELECTION,
    ResearchState.READY_FOR_SUBMISSION,
]


def test_idea_to_question_defined_allowed():
    assert is_transition_allowed(ResearchState.IDEA, ResearchState.QUESTION_DEFINED) is True


def test_idea_to_framework_defined_rejected():
    assert is_transition_allowed(ResearchState.IDEA, ResearchState.FRAMEWORK_DEFINED) is False


def test_idea_to_design_selected_rejected():
    assert is_transition_allowed(ResearchState.IDEA, ResearchState.DESIGN_SELECTED) is False


def test_question_defined_to_framework_defined_allowed():
    assert is_transition_allowed(
        ResearchState.QUESTION_DEFINED, ResearchState.FRAMEWORK_DEFINED
    ) is True


def test_question_defined_to_design_selected_rejected():
    assert is_transition_allowed(
        ResearchState.QUESTION_DEFINED, ResearchState.DESIGN_SELECTED
    ) is False


def test_all_sequential_transitions_allowed():
    for i in range(len(_ORDERED) - 1):
        assert is_transition_allowed(_ORDERED[i], _ORDERED[i + 1]) is True


def test_all_skip_forward_transitions_rejected():
    for i in range(len(_ORDERED)):
        for j in range(i + 2, len(_ORDERED)):
            assert is_transition_allowed(_ORDERED[i], _ORDERED[j]) is False


def test_backwards_transitions_rejected():
    for i in range(1, len(_ORDERED)):
        for j in range(0, i):
            assert is_transition_allowed(_ORDERED[i], _ORDERED[j]) is False


def test_same_state_transitions_rejected():
    for state in _ORDERED:
        assert is_transition_allowed(state, state) is False


def test_terminal_state_has_no_outgoing_transition():
    assert ResearchState.READY_FOR_SUBMISSION not in ALLOWED_TRANSITIONS
