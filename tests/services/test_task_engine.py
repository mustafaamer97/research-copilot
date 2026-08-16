"""Tests for the Task Engine."""
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
from domain.task import TaskPriority, TaskStatus
from services.task_engine import generate_tasks_for_project


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
# Rule 1 — missing research question
# ---------------------------------------------------------------------------

def test_idea_missing_question_generates_one_task():
    project = _project(state=ResearchState.IDEA)
    tasks = generate_tasks_for_project(project)
    assert len(tasks) == 1
    assert tasks[0].title == "Define research question"


def test_idea_missing_question_task_is_high_priority():
    project = _project(state=ResearchState.IDEA)
    tasks = generate_tasks_for_project(project)
    assert tasks[0].priority == TaskPriority.HIGH


def test_idea_missing_question_task_is_todo():
    project = _project(state=ResearchState.IDEA)
    tasks = generate_tasks_for_project(project)
    assert tasks[0].status == TaskStatus.TODO


def test_idea_missing_question_task_origin_is_system():
    project = _project(state=ResearchState.IDEA)
    tasks = generate_tasks_for_project(project)
    assert tasks[0].origin == ActorType.SYSTEM


def test_idea_with_question_generates_no_question_task():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    tasks = generate_tasks_for_project(project)
    titles = [t.title for t in tasks]
    assert "Define research question" not in titles


# ---------------------------------------------------------------------------
# Rule 2 — missing framework
# ---------------------------------------------------------------------------

def test_question_defined_without_framework_generates_framework_task():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    tasks = generate_tasks_for_project(project)
    titles = [t.title for t in tasks]
    assert "Define research framework" in titles


def test_question_defined_with_complete_pico_generates_no_component_tasks():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    tasks = generate_tasks_for_project(project)
    assert tasks == []


# ---------------------------------------------------------------------------
# Rule 3 — incomplete PICO
# ---------------------------------------------------------------------------

def test_incomplete_pico_missing_all_generates_four_tasks():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(type=FrameworkType.PICO),
    )
    tasks = generate_tasks_for_project(project)
    titles = {t.title for t in tasks}
    assert "Define population" in titles
    assert "Define intervention" in titles
    assert "Define comparator" in titles
    assert "Define primary outcome" in titles
    assert len(tasks) == 4


def test_incomplete_pico_missing_intervention_generates_one_task():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(
            type=FrameworkType.PICO,
            population=Population(description="Adults"),
            comparator=Comparator(description="Placebo"),
            outcome=Outcome(description="Mortality"),
        ),
    )
    tasks = generate_tasks_for_project(project)
    assert len(tasks) == 1
    assert tasks[0].title == "Define intervention"


def test_incomplete_pico_missing_population_generates_one_task():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(
            type=FrameworkType.PICO,
            intervention=Intervention(description="Drug A"),
            comparator=Comparator(description="Placebo"),
            outcome=Outcome(description="Mortality"),
        ),
    )
    tasks = generate_tasks_for_project(project)
    assert len(tasks) == 1
    assert tasks[0].title == "Define population"


# ---------------------------------------------------------------------------
# Rule 3 — incomplete PECO
# ---------------------------------------------------------------------------

def test_incomplete_peco_missing_all_generates_four_tasks():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(type=FrameworkType.PECO),
    )
    tasks = generate_tasks_for_project(project)
    titles = {t.title for t in tasks}
    assert "Define population" in titles
    assert "Define exposure" in titles
    assert "Define comparator" in titles
    assert "Define primary outcome" in titles
    assert len(tasks) == 4


def test_incomplete_peco_missing_exposure_generates_one_task():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(
            type=FrameworkType.PECO,
            population=Population(description="Adults"),
            comparator=Comparator(description="Non-smokers"),
            outcome=Outcome(description="Lung cancer"),
        ),
    )
    tasks = generate_tasks_for_project(project)
    assert len(tasks) == 1
    assert tasks[0].title == "Define exposure"


def test_incomplete_peco_with_complete_peco_generates_no_tasks():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_peco(),
    )
    tasks = generate_tasks_for_project(project)
    assert tasks == []


# ---------------------------------------------------------------------------
# Non-applicable fields are never turned into tasks
# ---------------------------------------------------------------------------

def test_pico_exposure_not_applicable_no_exposure_task():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(
            type=FrameworkType.PICO,
            population=Population(description="Adults"),
            intervention=Intervention(description="Drug A"),
            comparator=Comparator(description="Placebo"),
            outcome=Outcome(description="Mortality"),
        ),
    )
    tasks = generate_tasks_for_project(project)
    titles = [t.title for t in tasks]
    assert "Define exposure" not in titles


def test_peco_intervention_not_applicable_no_intervention_task():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(
            type=FrameworkType.PECO,
            population=Population(description="Adults"),
            exposure=Exposure(description="Smoking"),
            comparator=Comparator(description="Non-smokers"),
            outcome=Outcome(description="Lung cancer"),
        ),
    )
    tasks = generate_tasks_for_project(project)
    titles = [t.title for t in tasks]
    assert "Define intervention" not in titles


# ---------------------------------------------------------------------------
# Duplicate prevention
# ---------------------------------------------------------------------------

def test_existing_todo_task_not_duplicated():
    from domain.task import ResearchTask

    project = _project(state=ResearchState.IDEA)
    existing = ResearchTask(
        title="Define research question",
        reason="Already present.",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        origin=ActorType.SYSTEM,
    )
    project.tasks.append(existing)
    tasks = generate_tasks_for_project(project)
    assert all(t.title != "Define research question" for t in tasks)


def test_existing_in_progress_task_not_duplicated():
    from domain.task import ResearchTask

    project = _project(state=ResearchState.IDEA)
    existing = ResearchTask(
        title="Define research question",
        reason="In progress.",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        origin=ActorType.SYSTEM,
    )
    project.tasks.append(existing)
    tasks = generate_tasks_for_project(project)
    assert all(t.title != "Define research question" for t in tasks)


def test_completed_task_does_not_hide_missing_requirement():
    from domain.task import ResearchTask

    project = _project(state=ResearchState.IDEA)
    completed = ResearchTask(
        title="Define research question",
        reason="Was done earlier.",
        status=TaskStatus.COMPLETED,
        priority=TaskPriority.HIGH,
        origin=ActorType.SYSTEM,
    )
    project.tasks.append(completed)
    # research_question is still None — requirement is actually missing
    tasks = generate_tasks_for_project(project)
    titles = [t.title for t in tasks]
    assert "Define research question" in titles


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_task_generation_does_not_mutate_project_tasks():
    project = _project(state=ResearchState.IDEA)
    original_task_count = len(project.tasks)
    generate_tasks_for_project(project)
    assert len(project.tasks) == original_task_count


def test_task_generation_does_not_mutate_project_state():
    project = _project(state=ResearchState.IDEA)
    generate_tasks_for_project(project)
    assert project.state == ResearchState.IDEA


# ---------------------------------------------------------------------------
# All generated tasks use correct defaults
# ---------------------------------------------------------------------------

def test_all_generated_tasks_use_system_origin():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(type=FrameworkType.PICO),
    )
    tasks = generate_tasks_for_project(project)
    for task in tasks:
        assert task.origin == ActorType.SYSTEM


def test_all_generated_tasks_use_high_priority():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(type=FrameworkType.PICO),
    )
    tasks = generate_tasks_for_project(project)
    for task in tasks:
        assert task.priority == TaskPriority.HIGH


def test_all_generated_tasks_use_todo_status():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=ResearchFramework(type=FrameworkType.PICO),
    )
    tasks = generate_tasks_for_project(project)
    for task in tasks:
        assert task.status == TaskStatus.TODO


# ---------------------------------------------------------------------------
# States without rules return empty list
# ---------------------------------------------------------------------------

def test_unhandled_state_returns_empty_list():
    project = _project(state=ResearchState.PROTOCOL_READY)
    tasks = generate_tasks_for_project(project)
    assert tasks == []


def test_framework_defined_state_returns_empty_list():
    project = _project(state=ResearchState.FRAMEWORK_DEFINED)
    tasks = generate_tasks_for_project(project)
    assert tasks == []
