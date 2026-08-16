"""Public API contract tests."""
import pytest


# ---------------------------------------------------------------------------
# Import surface — domain
# ---------------------------------------------------------------------------

def test_domain_research_project_importable():
    from domain import ResearchProject
    assert ResearchProject is not None


def test_domain_research_question_importable():
    from domain import ResearchQuestion
    assert ResearchQuestion is not None


def test_domain_research_framework_importable():
    from domain import ResearchFramework
    assert ResearchFramework is not None


def test_domain_framework_type_importable():
    from domain import FrameworkType
    assert FrameworkType is not None


def test_domain_population_importable():
    from domain import Population
    assert Population is not None


def test_domain_intervention_importable():
    from domain import Intervention
    assert Intervention is not None


def test_domain_exposure_importable():
    from domain import Exposure
    assert Exposure is not None


def test_domain_comparator_importable():
    from domain import Comparator
    assert Comparator is not None


def test_domain_outcome_importable():
    from domain import Outcome
    assert Outcome is not None


def test_domain_research_task_importable():
    from domain import ResearchTask
    assert ResearchTask is not None


def test_domain_task_status_importable():
    from domain import TaskStatus
    assert TaskStatus is not None


def test_domain_task_priority_importable():
    from domain import TaskPriority
    assert TaskPriority is not None


def test_domain_research_state_importable():
    from domain import ResearchState
    assert ResearchState is not None


def test_domain_actor_type_importable():
    from domain import ActorType
    assert ActorType is not None


def test_domain_transition_record_importable():
    from domain import TransitionRecord
    assert TransitionRecord is not None


# ---------------------------------------------------------------------------
# Import surface — state_machine
# ---------------------------------------------------------------------------

def test_state_machine_allowed_transitions_importable():
    from state_machine import ALLOWED_TRANSITIONS
    assert ALLOWED_TRANSITIONS is not None


def test_state_machine_is_transition_allowed_importable():
    from state_machine import is_transition_allowed
    assert callable(is_transition_allowed)


def test_state_machine_gate_status_importable():
    from state_machine import GateStatus
    assert GateStatus is not None


def test_state_machine_gate_result_importable():
    from state_machine import GateResult
    assert GateResult is not None


def test_state_machine_check_gate_importable():
    from state_machine import check_gate
    assert callable(check_gate)


def test_state_machine_state_manager_importable():
    from state_machine import StateManager
    assert StateManager is not None


def test_state_machine_invalid_transition_error_importable():
    from state_machine import InvalidTransitionError
    assert issubclass(InvalidTransitionError, Exception)


def test_state_machine_gate_blocked_error_importable():
    from state_machine import GateBlockedError
    assert issubclass(GateBlockedError, Exception)


# ---------------------------------------------------------------------------
# Import surface — services
# ---------------------------------------------------------------------------

def test_services_generate_tasks_importable():
    from services import generate_tasks_for_project
    assert callable(generate_tasks_for_project)


# ---------------------------------------------------------------------------
# Import surface — repositories
# ---------------------------------------------------------------------------

def test_repositories_in_memory_repo_importable():
    from repositories import InMemoryProjectRepository
    assert InMemoryProjectRepository is not None


# ---------------------------------------------------------------------------
# Forbidden names — domain
# ---------------------------------------------------------------------------

def test_domain_has_no_project_state():
    import domain
    assert not hasattr(domain, "ProjectState")


def test_domain_has_no_research_state_enum():
    import domain
    assert not hasattr(domain, "ResearchStateEnum")


def test_domain_has_no_research_status():
    import domain
    assert not hasattr(domain, "ResearchStatus")


def test_domain_has_no_project_status():
    import domain
    assert not hasattr(domain, "ProjectStatus")


def test_domain_has_no_study_design():
    import domain
    assert not hasattr(domain, "StudyDesign")


def test_domain_has_no_analysis_plan():
    import domain
    assert not hasattr(domain, "AnalysisPlan")


def test_domain_has_no_literature_record():
    import domain
    assert not hasattr(domain, "LiteratureRecord")


def test_domain_has_no_screening_decision():
    import domain
    assert not hasattr(domain, "ScreeningDecision")


def test_domain_has_no_manuscript():
    import domain
    assert not hasattr(domain, "Manuscript")


def test_domain_has_no_journal():
    import domain
    assert not hasattr(domain, "Journal")


# ---------------------------------------------------------------------------
# No backward-compatibility aliases
# ---------------------------------------------------------------------------

def test_no_project_state_alias_in_state_module():
    import domain.state as m
    assert not hasattr(m, "ProjectState")
    assert not hasattr(m, "ResearchStateEnum")
    assert not hasattr(m, "ResearchStatus")
    assert not hasattr(m, "ProjectStatus")


def test_research_state_is_sole_lifecycle_type():
    from domain import ResearchState
    import domain.state as m
    # ResearchState must be the only lifecycle enum present
    from enum import EnumMeta
    lifecycle_enums = [
        name for name in dir(m)
        if isinstance(getattr(m, name), EnumMeta)
        and name not in ("ResearchState",)
    ]
    assert lifecycle_enums == [], f"Unexpected lifecycle enums: {lifecycle_enums}"


# ---------------------------------------------------------------------------
# No circular imports
# ---------------------------------------------------------------------------

def test_domain_imports_independently():
    import importlib
    importlib.import_module("domain")


def test_state_machine_imports_independently():
    import importlib
    importlib.import_module("state_machine")


def test_services_imports_independently():
    import importlib
    importlib.import_module("services")


def test_repositories_imports_independently():
    import importlib
    importlib.import_module("repositories")


# ---------------------------------------------------------------------------
# API contract workflow test — public imports only
# ---------------------------------------------------------------------------

def test_full_workflow_via_public_api():
    from domain import (
        ActorType,
        Comparator,
        FrameworkType,
        Intervention,
        Outcome,
        Population,
        ResearchFramework,
        ResearchProject,
        ResearchQuestion,
        ResearchState,
    )
    from repositories import InMemoryProjectRepository
    from services import generate_tasks_for_project
    from state_machine import (
        GateStatus,
        StateManager,
        check_gate,
    )

    # Create project
    project = ResearchProject(title="Public API Study", idea="Test idea.")
    assert project.state == ResearchState.IDEA

    # Generate tasks — question missing
    tasks = generate_tasks_for_project(project)
    assert any(t.title == "Define research question" for t in tasks)

    # Check gate — blocked
    gate = check_gate(project, ResearchState.QUESTION_DEFINED)
    assert gate.status == GateStatus.BLOCKED

    # Add question
    project.research_question = ResearchQuestion(text="Does X reduce Y in adults?")

    # Check gate — passes
    gate = check_gate(project, ResearchState.QUESTION_DEFINED)
    assert gate.status == GateStatus.PASS

    # Transition
    sm = StateManager()
    record = sm.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.QUESTION_DEFINED
    assert record.actor == ActorType.RESEARCHER

    # Add complete PICO framework
    project.framework = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults over 65"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="All-cause mortality"),
    )
    assert project.framework.is_complete is True

    # Transition to FRAMEWORK_DEFINED
    sm.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.FRAMEWORK_DEFINED

    # Save and retrieve
    repo = InMemoryProjectRepository()
    repo.save(project)
    restored = repo.get(project.id)

    assert restored.id == project.id
    assert restored.state == ResearchState.FRAMEWORK_DEFINED
    assert restored.research_question.text == "Does X reduce Y in adults?"
    assert restored.framework.is_complete is True
    assert len(restored.transition_history) == 2
