"""Tests for the Next Action Engine."""
import pytest

from domain.framework import (
    Comparator,
    Exposure,
    FrameworkType,
    Intervention,
    Outcome,
    Population,
    ResearchFramework,
)
from domain.project import ResearchProject
from domain.research_question import ResearchQuestion
from domain.state import ResearchState
from services.next_action import NextAction, NextActionPriority, get_next_action


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project(**kwargs) -> ResearchProject:
    defaults = dict(title="Study", idea="An idea.")
    defaults.update(kwargs)
    return ResearchProject(**defaults)


def _complete_pico() -> ResearchFramework:
    return ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )


def _complete_peco() -> ResearchFramework:
    return ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        exposure=Exposure(description="Smoking"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer"),
    )


# ---------------------------------------------------------------------------
# IDEA state
# ---------------------------------------------------------------------------

def test_idea_missing_question_action():
    project = _project(state=ResearchState.IDEA)
    result = get_next_action(project)
    assert result.action == "Define research question"


def test_idea_missing_question_priority():
    project = _project(state=ResearchState.IDEA)
    result = get_next_action(project)
    assert result.priority == NextActionPriority.HIGH


def test_idea_missing_question_not_blocked():
    project = _project(state=ResearchState.IDEA)
    result = get_next_action(project)
    assert result.blocked is False


def test_idea_missing_question_has_reason():
    project = _project(state=ResearchState.IDEA)
    result = get_next_action(project)
    assert result.reason and len(result.reason) > 0


def test_idea_with_question_action():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    result = get_next_action(project)
    assert result.action == "Define research framework"


def test_idea_with_question_priority():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    result = get_next_action(project)
    assert result.priority == NextActionPriority.HIGH


def test_idea_with_question_not_blocked():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    result = get_next_action(project)
    assert result.blocked is False


# ---------------------------------------------------------------------------
# QUESTION_DEFINED state
# ---------------------------------------------------------------------------

def test_question_defined_missing_framework_action():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    result = get_next_action(project)
    assert result.action == "Define research framework"


def test_question_defined_missing_framework_priority():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    result = get_next_action(project)
    assert result.priority == NextActionPriority.HIGH


def test_question_defined_missing_framework_not_blocked():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    result = get_next_action(project)
    assert result.blocked is False


def test_question_defined_incomplete_pico_first_missing():
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    result = get_next_action(project)
    assert "Population" in result.action


def test_question_defined_pico_missing_intervention_only():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    result = get_next_action(project)
    assert "Intervention" in result.action


def test_question_defined_pico_missing_comparator_only():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    result = get_next_action(project)
    assert "Comparator" in result.action


def test_question_defined_pico_missing_outcome_only():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    result = get_next_action(project)
    assert "Outcome" in result.action


def test_question_defined_incomplete_peco_first_missing():
    fw = ResearchFramework(type=FrameworkType.PECO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    result = get_next_action(project)
    assert "Population" in result.action


def test_question_defined_peco_missing_exposure_only():
    fw = ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    result = get_next_action(project)
    assert "Exposure" in result.action


def test_question_defined_complete_pico_action():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    result = get_next_action(project)
    assert result.action == "Review study design recommendation"


def test_question_defined_complete_pico_priority():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    result = get_next_action(project)
    assert result.priority == NextActionPriority.HIGH


def test_question_defined_complete_peco_action():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_peco(),
    )
    result = get_next_action(project)
    assert result.action == "Review study design recommendation"


def test_question_defined_complete_framework_not_blocked():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    result = get_next_action(project)
    assert result.blocked is False


# ---------------------------------------------------------------------------
# FRAMEWORK_DEFINED state
# ---------------------------------------------------------------------------

def test_framework_defined_action():
    project = _project(state=ResearchState.FRAMEWORK_DEFINED)
    result = get_next_action(project)
    assert result.action == "Select study design"


def test_framework_defined_priority():
    project = _project(state=ResearchState.FRAMEWORK_DEFINED)
    result = get_next_action(project)
    assert result.priority == NextActionPriority.HIGH


def test_framework_defined_not_blocked():
    project = _project(state=ResearchState.FRAMEWORK_DEFINED)
    result = get_next_action(project)
    assert result.blocked is False


def test_framework_defined_has_reason():
    project = _project(state=ResearchState.FRAMEWORK_DEFINED)
    result = get_next_action(project)
    assert result.reason and len(result.reason) > 0


# ---------------------------------------------------------------------------
# DESIGN_SELECTED state
# ---------------------------------------------------------------------------

def test_design_selected_action():
    project = _project(state=ResearchState.DESIGN_SELECTED)
    result = get_next_action(project)
    assert result.action == "Prepare research protocol"


def test_design_selected_priority():
    project = _project(state=ResearchState.DESIGN_SELECTED)
    result = get_next_action(project)
    assert result.priority == NextActionPriority.HIGH


def test_design_selected_not_blocked():
    project = _project(state=ResearchState.DESIGN_SELECTED)
    result = get_next_action(project)
    assert result.blocked is False


# ---------------------------------------------------------------------------
# Future states — safe fallback
# ---------------------------------------------------------------------------

_FUTURE_STATES = [
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


def test_future_states_return_safe_fallback():
    for state in _FUTURE_STATES:
        project = _project(state=state)
        result = get_next_action(project)
        assert result.action == "Continue research workflow", (
            f"Expected fallback for {state}, got: {result.action}"
        )


def test_future_states_priority_low():
    for state in _FUTURE_STATES:
        project = _project(state=state)
        result = get_next_action(project)
        assert result.priority == NextActionPriority.LOW, (
            f"Expected LOW priority for {state}"
        )


def test_future_states_not_blocked():
    for state in _FUTURE_STATES:
        project = _project(state=state)
        result = get_next_action(project)
        assert result.blocked is False


def test_future_states_have_reason():
    for state in _FUTURE_STATES:
        project = _project(state=state)
        result = get_next_action(project)
        assert result.reason and len(result.reason) > 0


# ---------------------------------------------------------------------------
# Integrity — no mutation
# ---------------------------------------------------------------------------

def test_does_not_mutate_project_state():
    project = _project(state=ResearchState.IDEA)
    get_next_action(project)
    assert project.state == ResearchState.IDEA


def test_does_not_mutate_framework():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(type=FrameworkType.PICO),
    )
    get_next_action(project)
    assert project.framework.population is None


def test_does_not_modify_research_question():
    project = _project(state=ResearchState.IDEA)
    get_next_action(project)
    assert project.research_question is None


def test_does_not_create_tasks():
    project = _project(state=ResearchState.IDEA)
    get_next_action(project)
    assert project.tasks == []


def test_does_not_create_transition_record():
    project = _project(state=ResearchState.IDEA)
    get_next_action(project)
    assert project.transition_history == []


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_deterministic_idea_missing_question():
    project = _project(state=ResearchState.IDEA)
    r1 = get_next_action(project)
    r2 = get_next_action(project)
    assert r1.action == r2.action
    assert r1.reason == r2.reason
    assert r1.priority == r2.priority


def test_deterministic_question_defined_incomplete():
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    r1 = get_next_action(project)
    r2 = get_next_action(project)
    assert r1.action == r2.action
    assert r1.reason == r2.reason


def test_deterministic_complete_pico():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    r1 = get_next_action(project)
    r2 = get_next_action(project)
    assert r1.action == r2.action


# ---------------------------------------------------------------------------
# Integration — uses existing engines
# ---------------------------------------------------------------------------

def test_uses_missing_information_engine_for_first_component():
    from services.missing_information import get_missing_information
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    missing = get_missing_information(project)
    next_action = get_next_action(project)
    assert missing[0].field in next_action.action


def test_uses_framework_is_complete_for_complete_case():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    assert project.framework.is_complete is True
    result = get_next_action(project)
    assert result.action == "Review study design recommendation"


# ---------------------------------------------------------------------------
# Result model integrity
# ---------------------------------------------------------------------------

def test_result_is_next_action_model():
    project = _project(state=ResearchState.IDEA)
    result = get_next_action(project)
    assert isinstance(result, NextAction)


def test_result_has_all_required_fields():
    project = _project(state=ResearchState.IDEA)
    result = get_next_action(project)
    assert hasattr(result, "action")
    assert hasattr(result, "reason")
    assert hasattr(result, "priority")
    assert hasattr(result, "blocked")


# ---------------------------------------------------------------------------
# Public import
# ---------------------------------------------------------------------------

def test_get_next_action_importable_from_services():
    from services import get_next_action as fn
    assert callable(fn)


def test_next_action_model_importable_from_services():
    from services import NextAction
    assert NextAction is not None
