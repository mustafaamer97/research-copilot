"""Tests for StateManager."""
import pytest
from datetime import timezone

from domain.actors import ActorType
from domain.framework import (
    Comparator,
    FrameworkType,
    Intervention,
    Outcome,
    Population,
    ResearchFramework,
)
from domain.project import ResearchProject
from domain.research_question import ResearchQuestion
from domain.state import ResearchState
from state_machine.manager import GateBlockedError, InvalidTransitionError, StateManager


def _base_project(**kwargs) -> ResearchProject:
    defaults = dict(title="Study", idea="An idea.")
    defaults.update(kwargs)
    return ResearchProject(**defaults)


def _project_with_question() -> ResearchProject:
    return _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )


def _project_at_question_defined() -> ResearchProject:
    p = _project_with_question()
    p.state = ResearchState.QUESTION_DEFINED
    p.framework = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    return p


manager = StateManager()


# --- Successful transition ---

def test_successful_transition_changes_state():
    project = _project_with_question()
    manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.QUESTION_DEFINED


def test_successful_transition_creates_record():
    project = _project_with_question()
    record = manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert record is not None
    assert record.from_state == ResearchState.IDEA
    assert record.to_state == ResearchState.QUESTION_DEFINED


def test_successful_transition_appends_history():
    project = _project_with_question()
    assert len(project.transition_history) == 0
    manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert len(project.transition_history) == 1


def test_actor_preserved_in_record():
    project = _project_with_question()
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    assert record.actor == ActorType.RESEARCHER


def test_reason_preserved_in_record():
    project = _project_with_question()
    record = manager.transition(
        project,
        ResearchState.QUESTION_DEFINED,
        ActorType.RESEARCHER,
        reason="Researcher confirmed.",
    )
    assert record.reason == "Researcher confirmed."


def test_default_reason_used_when_none():
    project = _project_with_question()
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    assert record.reason is not None
    assert len(record.reason) > 0


def test_transition_timestamp_is_utc():
    project = _project_with_question()
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    assert record.timestamp.tzinfo == timezone.utc


def test_record_project_id_matches():
    project = _project_with_question()
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    assert record.project_id == project.id


# --- Invalid structural transition ---

def test_invalid_transition_raises_invalid_transition_error():
    project = _base_project()
    with pytest.raises(InvalidTransitionError):
        manager.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)


def test_invalid_transition_does_not_mutate_state():
    project = _base_project()
    with pytest.raises(InvalidTransitionError):
        manager.transition(project, ResearchState.DESIGN_SELECTED, ActorType.RESEARCHER)
    assert project.state == ResearchState.IDEA


def test_invalid_transition_does_not_append_history():
    project = _base_project()
    with pytest.raises(InvalidTransitionError):
        manager.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)
    assert len(project.transition_history) == 0


def test_backwards_transition_raises_invalid_transition_error():
    project = _project_with_question()
    manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    with pytest.raises(InvalidTransitionError):
        manager.transition(project, ResearchState.IDEA, ActorType.RESEARCHER)


# --- Blocked gate ---

def test_blocked_gate_raises_gate_blocked_error():
    project = _base_project()
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)


def test_blocked_gate_does_not_mutate_state():
    project = _base_project()
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.IDEA


def test_blocked_gate_does_not_append_history():
    project = _base_project()
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert len(project.transition_history) == 0


def 
