"""Integration tests — intelligence services and state machine gates agree."""
import pytest

from domain.actors import ActorType
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
from services.framework_validator import FrameworkValidationStatus, validate_framework
from services.missing_information import get_missing_information
from services.next_action import get_next_action
from services.study_design_recommender import recommend_study_design
from state_machine.gates import GateStatus, check_gate
from state_machine.manager import GateBlockedError, InvalidTransitionError, StateManager

manager = StateManager()


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
# 1. IDEA — missing question: all three systems agree
# ---------------------------------------------------------------------------

def test_idea_missing_question_missing_information_reports_it():
    project = _project(state=ResearchState.IDEA)
    missing = get_missing_information(project)
    fields = [m.field for m in missing]
    assert "research_question" in fields


def test_idea_missing_question_next_action_agrees():
    project = _project(state=ResearchState.IDEA)
    action = get_next_action(project)
    assert action.action == "Define research question"


def test_idea_missing_question_gate_blocks_transition():
    project = _project(state=ResearchState.IDEA)
    gate = check_gate(project, ResearchState.QUESTION_DEFINED)
    assert gate.status == GateStatus.BLOCKED


def test_idea_missing_question_state_manager_raises():
    project = _project(state=ResearchState.IDEA)
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)


def test_idea_missing_question_three_systems_agree():
    project = _project(state=ResearchState.IDEA)
    missing = get_missing_information(project)
    action = get_next_action(project)
    gate = check_gate(project, ResearchState.QUESTION_DEFINED)
    assert any(m.field == "research_question" for m in missing)
    assert "research question" in action.action.lower()
    assert gate.status == GateStatus.BLOCKED


# ---------------------------------------------------------------------------
# 2. IDEA → QUESTION_DEFINED after question added
# ---------------------------------------------------------------------------

def test_idea_with_question_missing_information_empty():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    assert get_missing_information(project) == []


def test_idea_with_question_gate_passes():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    gate = check_gate(project, ResearchState.QUESTION_DEFINED)
    assert gate.status == GateStatus.PASS


def test_idea_with_question_transition_succeeds():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.QUESTION_DEFINED


def test_idea_with_question_exactly_one_record():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert len(project.transition_history) == 1


def test_idea_with_question_record_fields():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    assert record.from_state == ResearchState.IDEA
    assert record.to_state == ResearchState.QUESTION_DEFINED


# ---------------------------------------------------------------------------
# 3. QUESTION_DEFINED — missing framework: three systems agree
# ---------------------------------------------------------------------------

def test_question_defined_no_framework_missing_information_reports_it():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    missing = get_missing_information(project)
    fields = [m.field for m in missing]
    assert "framework" in fields


def test_question_defined_no_framework_next_action_agrees():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    action = get_next_action(project)
    assert action.action == "Define research framework"


def test_question_defined_no_framework_gate_blocks():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    gate = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert gate.status == GateStatus.BLOCKED


def test_question_defined_no_framework_state_manager_raises():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)


def test_question_defined_no_framework_three_systems_agree():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    missing = get_missing_information(project)
    action = get_next_action(project)
    gate = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert any(m.field == "framework" for m in missing)
    assert "framework" in action.action.lower()
    assert gate.status == GateStatus.BLOCKED


# ---------------------------------------------------------------------------
# 4. INCOMPLETE PICO — all four systems agree
# ---------------------------------------------------------------------------

def test_incomplete_pico_validation_incomplete():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    result = validate_framework(fw)
    assert result.status == FrameworkValidationStatus.INCOMPLETE


def test_incomplete_pico_missing_information_reports_comparator():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    missing = get_missing_information(project)
    fields = [m.field for m in missing]
    assert "Comparator" in fields


def test_incomplete_pico_next_action_mentions_comparator():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    action = get_next_action(project)
    assert "Comparator" in action.action


def test_incomplete_pico_gate_blocked():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    gate = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert gate.status == GateStatus.BLOCKED


def test_incomplete_pico_four_systems_agree():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    val = validate_framework(fw)
    missing = get_missing_information(project)
    action = get_next_action(project)
    gate = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert val.status == FrameworkValidationStatus.INCOMPLETE
    assert any(m.field == "Comparator" for m in missing)
    assert "Comparator" in action.action
    assert gate.status == GateStatus.BLOCKED


# ---------------------------------------------------------------------------
# 5. COMPLETE PICO — all four systems agree
# ---------------------------------------------------------------------------

def test_complete_pico_validation_complete():
    result = validate_framework(_complete_pico())
    assert result.status == FrameworkValidationStatus.COMPLETE


def test_complete_pico_missing_information_empty():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    assert get_missing_information(project) == []


def test_complete_pico_next_action_review_recommendation():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    action = get_next_action(project)
    assert action.action == "Review study design recommendation"


def test_complete_pico_gate_passes():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    gate = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert gate.status == GateStatus.PASS


def test_complete_pico_four_systems_agree():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    val = validate_framework(project.framework)
    missing = get_missing_information(project)
    action = get_next_action(project)
    gate = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert val.status == FrameworkValidationStatus.COMPLETE
    assert missing == []
    assert action.action == "Review study design recommendation"
    assert gate.status == GateStatus.PASS


def test_complete_pico_transition_succeeds():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    manager.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.FRAMEWORK_DEFINED


# ---------------------------------------------------------------------------
# 6. COMPLETE PECO — all four systems agree
# ---------------------------------------------------------------------------

def test_complete_peco_validation_complete():
    result = validate_framework(_complete_peco())
    assert result.status == FrameworkValidationStatus.COMPLETE


def test_complete_peco_missing_information_empty():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_peco(),
    )
    assert get_missing_information(project) == []


def test_complete_peco_next_action_review_recommendation():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_peco(),
    )
    action = get_next_action(project)
    assert action.action == "Review study design recommendation"


def test_complete_peco_gate_passes():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_peco(),
    )
    gate = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert gate.status == GateStatus.PASS


def test_complete_peco_intervention_never_reported_missing():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_peco(),
    )
    missing = get_missing_information(project)
    fields = [m.field for m in missing]
    assert "Intervention" not in fields


def test_complete_peco_four_systems_agree():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_peco(),
    )
    val = validate_framework(project.framework)
    missing = get_missing_information(project)
    action = get_next_action(project)
    gate = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert val.status == FrameworkValidationStatus.COMPLETE
    assert missing == []
    assert action.action == "Review study design recommendation"
    assert gate.status == GateStatus.PASS


# ---------------------------------------------------------------------------
# 7. FRAMEWORK_DEFINED — next action and state manager
# ---------------------------------------------------------------------------

def test_framework_defined_next_action_select_design():
    project = _project(state=ResearchState.FRAMEWORK_DEFINED)
    action = get_next_action(project)
    assert action.action == "Select study design"


def test_framework_defined_design_not_auto_selected():
    project = _project(state=ResearchState.FRAMEWORK_DEFINED)
    get_next_action(project)
    assert project.state == ResearchState.FRAMEWORK_DEFINED
    assert not hasattr(project, "study_design") or getattr(project, "study_design", None) is None


def test_framework_defined_transition_to_design_selected_blocked_by_gate():
    project = _project(state=ResearchState.FRAMEWORK_DEFINED)
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.DESIGN_SELECTED, ActorType.RESEARCHER)
    assert project.state == ResearchState.FRAMEWORK_DEFINED


# ---------------------------------------------------------------------------
# 8. Study design recommendation — informational only
# ---------------------------------------------------------------------------

def test_recommendation_does_not_change_state():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    recommend_study_design(project)
    assert project.state == ResearchState.QUESTION_DEFINED


def test_recommendation_does_not_create_transition_record():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    recommend_study_design(project)
    assert len(project.transition_history) == 0


def test_recommendation_does_not_modify_framework():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    original_type = project.framework.type
    recommend_study_design(project)
    assert project.framework.type == original_type


def test_recommendation_does_not_set_study_design_on_project():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    recommend_study_design(project)
    assert not hasattr(project, "study_design") or getattr(project, "study_design", None) is None


# ---------------------------------------------------------------------------
# 9. Single source of truth — only StateManager controls transitions
# ---------------------------------------------------------------------------

def test_next_action_does_not_perform_transition():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    get_next_action(project)
    assert project.state == ResearchState.IDEA
    assert project.transition_history == []


def test_missing_information_does_not_perform_transition():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    get_missing_information(project)
    assert project.state == ResearchState.IDEA
    assert project.transition_history == []


def test_framework_validation_does_not_perform_transition():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    validate_framework(project.framework)
    assert project.state == ResearchState.QUESTION_DEFINED
    assert project.transition_history == []


def test_check_gate_does_not_perform_transition():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    check_gate(project, ResearchState.QUESTION_DEFINED)
    assert project.state == ResearchState.IDEA
    assert project.transition_history == []


# ---------------------------------------------------------------------------
# 10. Atomicity — blocked transition leaves everything unchanged
# ---------------------------------------------------------------------------

def test_blocked_transition_state_unchanged():
    project = _project(state=ResearchState.IDEA)
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.IDEA


def test_blocked_transition_history_unchanged():
    project = _project(state=ResearchState.IDEA)
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert project.transition_history == []


def test_invalid_transition_state_unchanged():
    project = _project(state=ResearchState.IDEA)
    with pytest.raises(InvalidTransitionError):
        manager.transition(project, ResearchState.DESIGN_SELECTED, ActorType.RESEARCHER)
    assert project.state == ResearchState.IDEA


def test_invalid_transition_history_unchanged():
    project = _project(state=ResearchState.IDEA)
    with pytest.raises(InvalidTransitionError):
        manager.transition(project, ResearchState.DESIGN_SELECTED, ActorType.RESEARCHER)
    assert project.transition_history == []


def test_intelligence_services_cannot_mutate_after_blocked_transition():
    project = _project(state=ResearchState.IDEA)
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    missing = get_missing_information(project)
    action = get_next_action(project)
    assert project.state == ResearchState.IDEA
    assert project.transition_history == []
    assert any(m.field == "research_question" for m in missing)


# ---------------------------------------------------------------------------
# 11. Determinism — all services produce identical results on repeat calls
# ---------------------------------------------------------------------------

def test_all_services_deterministic_on_complete_pico():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    val1 = validate_framework(project.framework)
    val2 = validate_framework(project.framework)
    assert val1.status == val2.status
    assert val1.missing_components == val2.missing_components

    miss1 = get_missing_information(project)
    miss2 = get_missing_information(project)
    assert miss1 == miss2

    act1 = get_next_action(project)
    act2 = get_next_action(project)
    assert act1.action == act2.action
    assert act1.reason == act2.reason

    rec1 = recommend_study_design(project)
    rec2 = recommend_study_design(project)
    assert rec1.recommended_design == rec2.recommended_design
    assert rec1.alternatives == rec2.alternatives
    assert rec1.rationale == rec2.rationale


def test_all_services_deterministic_on_incomplete_pico():
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)

    val1 = validate_framework(fw)
    val2 = validate_framework(fw)
    assert val1.missing_components == val2.missing_components

    miss1 = get_missing_information(project)
    miss2 = get_missing_information(project)
    assert [m.field for m in miss1] == [m.field for m in miss2]

    act1 = get_next_action(project)
    act2 = get_next_action(project)
    assert act1.action == act2.action

    rec1 = recommend_study_design(project)
    rec2 = recommend_study_design(project)
    assert rec1.recommended_design == rec2.recommended_design


def test_services_produce_no_timestamps():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    val = validate_framework(project.framework)
    assert not hasattr(val, "timestamp")

    missing = get_missing_information(project)
    for m in missing:
        assert not hasattr(m, "timestamp")

    action = get_next_action(project)
    assert not hasattr(action, "timestamp")

    rec = recommend_study_design(project)
    assert not hasattr(rec, "timestamp")
