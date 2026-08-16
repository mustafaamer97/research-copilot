"""Tests for the gate engine."""
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
from state_machine.gates import GateStatus, check_gate


def _base_project(**kwargs) -> ResearchProject:
    defaults = dict(title="Test", idea="Test idea.")
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


# --- QUESTION_DEFINED gate ---

def test_missing_question_blocks_question_defined():
    project = _base_project()
    result = check_gate(project, ResearchState.QUESTION_DEFINED)
    assert result.status == GateStatus.BLOCKED
    assert result.reasons


def test_existing_question_passes_question_defined():
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )
    result = check_gate(project, ResearchState.QUESTION_DEFINED)
    assert result.status == GateStatus.PASS
    assert result.reasons == []


# --- FRAMEWORK_DEFINED gate ---

def test_missing_framework_blocks_framework_defined():
    project = _base_project()
    result = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert result.status == GateStatus.BLOCKED
    assert "missing" in result.reasons[0].lower()


def test_incomplete_framework_blocks_framework_defined():
    project = _base_project(
        framework=ResearchFramework(type=FrameworkType.PICO)
    )
    result = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert result.status == GateStatus.BLOCKED
    assert "incomplete" in result.reasons[0].lower()


def test_complete_pico_passes_framework_defined():
    project = _base_project(framework=_complete_pico())
    result = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert result.status == GateStatus.PASS
    assert result.reasons == []


def test_complete_peco_passes_framework_defined():
    project = _base_project(framework=_complete_peco())
    result = check_gate(project, ResearchState.FRAMEWORK_DEFINED)
    assert result.status == GateStatus.PASS
    assert result.reasons == []


# --- DESIGN_SELECTED gate ---

def test_design_selected_gate_blocked_not_implemented():
    project = _base_project()
    result = check_gate(project, ResearchState.DESIGN_SELECTED)
    assert result.status == GateStatus.BLOCKED
    assert result.reasons


def test_design_selected_reason_mentions_study_design():
    project = _base_project()
    result = check_gate(project, ResearchState.DESIGN_SELECTED)
    combined = " ".join(result.reasons).lower()
    assert "study design" in combined or "not implemented" in combined


# --- Unimplemented gates ---

def test_unimplemented_gate_returns_blocked():
    project = _base_project()
    result = check_gate(project, ResearchState.PROTOCOL_READY)
    assert result.status == GateStatus.BLOCKED
    assert result.reasons


def test_gate_does_not_mutate_project():
    project = _base_project()
    original_state = project.state
    check_gate(project, ResearchState.QUESTION_DEFINED)
    assert project.state == original_state
