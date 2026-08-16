"""Integration and contract tests for the canonical research lifecycle."""
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
from domain.task import TaskStatus
from domain.transition import TransitionRecord
from repositories.project_repository import (
    InMemoryProjectRepository,
    deserialize_project,
    serialize_project,
)
from services.task_engine import generate_tasks_for_project
from state_machine.gates import GateStatus, check_gate
from state_machine.manager import GateBlockedError, InvalidTransitionError, StateManager

manager = StateManager()


def _base_project(**kwargs) -> ResearchProject:
    defaults = dict(title="Study", idea="An idea.")
    defaults.update(kwargs)
    return ResearchProject(**defaults)


def _complete_pico() -> ResearchFramework:
    return ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults over 65"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="All-cause mortality"),
    )


def _complete_peco() -> ResearchFramework:
    return ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        exposure=Exposure(description="Cigarette smoking"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer incidence"),
    )


# ---------------------------------------------------------------------------
# TEST 1 — New project default state
# ---------------------------------------------------------------------------

def test_new_project_defaults():
    project = _base_project()
    assert project.state == ResearchState.IDEA
    assert project.research_question is None
    assert project.framework is None
    assert project.tasks == []
    assert project.transition_history == []


# ---------------------------------------------------------------------------
# TEST 2 — IDEA → QUESTION_DEFINED
# ---------------------------------------------------------------------------

def test_idea_to_question_defined_blocked_without_question():
    project = _base_project()
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.IDEA
    assert project.transition_history == []


def test_idea_to_question_defined_succeeds_with_question():
    project = _base_project()
    project.research_question = ResearchQuestion(text="Does X reduce Y?")
    manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.QUESTION_DEFINED


def test_idea_to_question_defined_creates_one_record():
    project = _base_project()
    project.research_question = ResearchQuestion(text="Does X reduce Y?")
    manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert len(project.transition_history) == 1


def test_idea_to_question_defined_record_fields():
    project = _base_project()
    project.research_question = ResearchQuestion(text="Does X reduce Y?")
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    assert record.from_state == ResearchState.IDEA
    assert record.to_state == ResearchState.QUESTION_DEFINED
    assert record.actor == ActorType.RESEARCHER


# ---------------------------------------------------------------------------
# TEST 3 — QUESTION_DEFINED → FRAMEWORK_DEFINED with complete PICO
# ---------------------------------------------------------------------------

def test_question_defined_to_framework_defined_with_complete_pico():
    project = _base_project(
        state=ResearchState.QUESTION_DEFINED,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
        framework=_complete_pico(),
    )
    manager.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.FRAMEWORK_DEFINED


def test_question_defined_to_framework_defined_record_correct():
    project = _base_project(
        state=ResearchState.QUESTION_DEFINED,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
        framework=_complete_pico(),
    )
    record = manager.transition(
        project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER
    )
    assert record.from_state == ResearchState.QUESTION_DEFINED
    assert record.to_state == ResearchState.FRAMEWORK_DEFINED
    assert record.actor == ActorType.RESEARCHER


# ---------------------------------------------------------------------------
# TEST 4 — Incomplete framework blocks FRAMEWORK_DEFINED
# ---------------------------------------------------------------------------

def test_incomplete_framework_blocks_transition():
    project = _base_project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(type=FrameworkType.PICO),
    )
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.QUESTION_DEFINED
    assert project.transition_history == []


def test_partially_complete_pico_blocks_transition():
    project = _base_project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(
            type=FrameworkType.PICO,
            population=Population(description="Adults"),
            intervention=Intervention(description="Drug A"),
        ),
    )
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.QUESTION_DEFINED


# ---------------------------------------------------------------------------
# TEST 5 — PECO complete framework succeeds
# ---------------------------------------------------------------------------

def test_complete_peco_framework_is_complete():
    fw = _complete_peco()
    assert fw.is_complete is True


def test_complete_peco_transitions_to_framework_defined():
    project = _base_project(
        state=ResearchState.QUESTION_DEFINED,
        research_question=ResearchQuestion(text="Does smoking cause lung cancer?"),
        framework=_complete_peco(),
    )
    manager.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.FRAMEWORK_DEFINED


# ---------------------------------------------------------------------------
# TEST 6 — Non-applicable components
# ---------------------------------------------------------------------------

def test_pico_does_not_require_exposure():
    fw = _complete_pico()
    assert fw.exposure is None
    assert fw.is_complete is True


def test_peco_does_not_require_intervention():
    fw = _complete_peco()
    assert fw.intervention is None
    assert fw.is_complete is True


def test_pico_no_exposure_task_generated():
    project = _base_project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(
            type=FrameworkType.PICO,
            population=Population(description="Adults"),
            comparator=Comparator(description="Placebo"),
            outcome=Outcome(description="Mortality"),
        ),
    )
    tasks = generate_tasks_for_project(project)
    titles = [t.title for t in tasks]
    assert "Define exposure" not in titles


def test_peco_no_intervention_task_generated():
    project = _base_project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(
            type=FrameworkType.PECO,
            population=Population(description="Adults"),
            comparator=Comparator(description="Non-smokers"),
            outcome=Outcome(description="Lung cancer"),
        ),
    )
    tasks = generate_tasks_for_project(project)
    titles = [t.title for t in tasks]
    assert "Define intervention" not in titles


# ---------------------------------------------------------------------------
# TEST 7 — Task Engine + Gate Engine
# ---------------------------------------------------------------------------

def test_task_engine_generates_question_task_when_gate_blocked():
    project = _base_project(state=ResearchState.IDEA)
    tasks = generate_tasks_for_project(project)
    assert len(tasks) == 1
    assert tasks[0].title == "Define research question"


def test_gate_blocked_without_question():
    project = _base_project(state=ResearchState.IDEA)
    result = check_gate(project, ResearchState.QUESTION_DEFINED)
    assert result.status == GateStatus.BLOCKED


def test_gate_passes_after_question_added():
    project = _base_project(state=ResearchState.IDEA)
    project.research_question = ResearchQuestion(text="Does X reduce Y?")
    result = check_gate(project, ResearchState.QUESTION_DEFINED)
    assert result.status == GateStatus.PASS


def test_no_question_task_generated_after_question_added():
    project = _base_project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    tasks = generate_tasks_for_project(project)
    titles = [t.title for t in tasks]
    assert "Define research question" not in titles


# ---------------------------------------------------------------------------
# TEST 8 — Full serialization round-trip with continuation
# ---------------------------------------------------------------------------

def test_full_project_round_trip_preserves_all_domain_values():
    project = _base_project(
        state=ResearchState.QUESTION_DEFINED,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
        framework=_complete_pico(),
    )
    from domain.task import ResearchTask, TaskPriority
    task = ResearchTask(
        title="Define population",
        reason="Missing.",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        origin=ActorType.SYSTEM,
    )
    project.tasks.append(task)
    record = TransitionRecord(
        project_id=project.id,
        from_state=ResearchState.IDEA,
        to_state=ResearchState.QUESTION_DEFINED,
        actor=ActorType.RESEARCHER,
        reason="Confirmed.",
    )
    project.transition_history.append(record)

    restored = deserialize_project(serialize_project(project))

    assert restored.id == project.id
    assert restored.title == project.title
    assert restored.idea == project.idea
    assert restored.state == ResearchState.QUESTION_DEFINED
    assert restored.research_question.text == "Does X reduce Y?"
    assert restored.framework.type == FrameworkType.PICO
    assert restored.framework.is_complete is True
    assert len(restored.tasks) == 1
    assert restored.tasks[0].title == "Define population"
    assert len(restored.transition_history) == 1
    assert restored.transition_history[0].from_state == ResearchState.IDEA


def test_restored_project_can_continue_through_state_manager():
    project = _base_project(
        state=ResearchState.QUESTION_DEFINED,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
        framework=_complete_pico(),
    )
    restored = deserialize_project(serialize_project(project))
    manager.transition(restored, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)
    assert restored.state == ResearchState.FRAMEWORK_DEFINED


# ---------------------------------------------------------------------------
# TEST 9 — Immutability of TransitionRecord
# ---------------------------------------------------------------------------

def test_transition_record_is_immutable():
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    with pytest.raises(Exception):
        record.reason = "Mutated reason"


def test_transition_record_from_state_immutable():
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    with pytest.raises(Exception):
        record.from_state = ResearchState.FRAMEWORK_DEFINED


# ---------------------------------------------------------------------------
# TEST 10 — Failed transition atomicity
# ---------------------------------------------------------------------------

def test_invalid_structural_transition_raises_and_does_not_mutate():
    project = _base_project()
    with pytest.raises(InvalidTransitionError):
        manager.transition(project, ResearchState.DESIGN_SELECTED, ActorType.RESEARCHER)
    assert project.state == ResearchState.IDEA
    assert project.transition_history == []


def test_valid_but_blocked_transition_raises_and_does_not_mutate():
    project = _base_project()
    with pytest.raises(GateBlockedError):
        manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.IDEA
    assert project.transition_history == []


def test_invalid_transition_skipping_multiple_states():
    project = _base_project()
    with pytest.raises(InvalidTransitionError):
        manager.transition(project, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)
    assert project.state == ResearchState.IDEA
    assert len(project.transition_history) == 0


# ---------------------------------------------------------------------------
# TEST 11 — Researcher vs System actor
# ---------------------------------------------------------------------------

def test_state_manager_preserves_researcher_actor():
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    assert record.actor == ActorType.RESEARCHER


def test_state_manager_preserves_system_actor():
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.SYSTEM
    )
    assert record.actor == ActorType.SYSTEM


def test_task_engine_generates_tasks_with_system_origin():
    project = _base_project(state=ResearchState.IDEA)
    tasks = generate_tasks_for_project(project)
    for task in tasks:
        assert task.origin == ActorType.SYSTEM


def test_actor_never_silently_changed():
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )
    for actor in ActorType:
        p = _base_project(
            research_question=ResearchQuestion(text="Does X reduce Y?")
        )
        record = manager.transition(p, ResearchState.QUESTION_DEFINED, actor)
        assert record.actor == actor


# ---------------------------------------------------------------------------
# TEST 12 — No duplicate source of truth
# ---------------------------------------------------------------------------

def test_project_has_no_population_attribute():
    project = _base_project()
    assert not hasattr(project, "population")


def test_project_has_no_intervention_attribute():
    project = _base_project()
    assert not hasattr(project, "intervention")


def test_project_has_no_exposure_attribute():
    project = _base_project()
    assert not hasattr(project, "exposure")


def test_project_has_no_comparator_attribute():
    project = _base_project()
    assert not hasattr(project, "comparator")


def test_project_has_no_outcome_attribute():
    project = _base_project()
    assert not hasattr(project, "outcome")


def test_framework_components_exist_under_framework():
    project = _base_project(framework=_complete_pico())
    assert project.framework.population is not None
    assert project.framework.intervention is not None
    assert project.framework.comparator is not None
    assert project.framework.outcome is not None


# ---------------------------------------------------------------------------
# TEST 13 — Single canonical state type
# ---------------------------------------------------------------------------

def test_only_research_state_exists_as_lifecycle_type():
    import domain.state as state_module
    for forbidden in ("ProjectState", "ResearchStateEnum", "ResearchStatus", "ProjectStatus"):
        assert not hasattr(state_module, forbidden), (
            f"Forbidden lifecycle type '{forbidden}' found in domain.state"
        )


def test_project_state_field_is_research_state():
    project = _base_project()
    assert isinstance(project.state, ResearchState)


def test_transition_record_states_are_research_state():
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )
    record = manager.transition(
        project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER
    )
    assert isinstance(record.from_state, ResearchState)
    assert isinstance(record.to_state, ResearchState)


def test_no_status_field_on_project():
    project = _base_project()
    assert not hasattr(project, "status")


# ---------------------------------------------------------------------------
# TEST 14 — Repository integration
# ---------------------------------------------------------------------------

def test_repository_save_and_restore_full_lifecycle():
    repo = InMemoryProjectRepository()
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )
    manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    repo.save(project)

    restored = repo.get(project.id)
    assert restored.state == ResearchState.QUESTION_DEFINED
    assert len(restored.transition_history) == 1
    assert restored.research_question.text == "Does X reduce Y?"


def test_repository_isolation_after_transition():
    repo = InMemoryProjectRepository()
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?"),
        framework=_complete_pico(),
    )
    manager.transition(project, ResearchState.QUESTION_DEFINED, ActorType.RESEARCHER)
    repo.save(project)

    retrieved = repo.get(project.id)
    manager.transition(retrieved, ResearchState.FRAMEWORK_DEFINED, ActorType.RESEARCHER)

    stored = repo.get(project.id)
    assert stored.state == ResearchState.QUESTION_DEFINED
