"""Tests for serialization and InMemoryProjectRepository."""
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

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
from domain.task import ResearchTask, TaskPriority, TaskStatus
from domain.transition import TransitionRecord
from repositories.project_repository import (
    InMemoryProjectRepository,
    deserialize_project,
    serialize_project,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_project(**kwargs) -> ResearchProject:
    defaults = dict(title="Study", idea="An idea.")
    defaults.update(kwargs)
    return ResearchProject(**defaults)


def _full_project() -> ResearchProject:
    project = _base_project(
        title="Full Project",
        idea="Comprehensive research idea.",
        state=ResearchState.QUESTION_DEFINED,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
        framework=ResearchFramework(
            type=FrameworkType.PICO,
            population=Population(description="Adults over 65"),
            intervention=Intervention(description="Drug A"),
            comparator=Comparator(description="Placebo"),
            outcome=Outcome(description="All-cause mortality"),
        ),
    )
    task = ResearchTask(
        title="Define population",
        reason="Missing population.",
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
        reason="Researcher confirmed.",
    )
    project.transition_history.append(record)
    return project


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def test_serialize_returns_string():
    project = _base_project()
    result = serialize_project(project)
    assert isinstance(result, str)


def test_serialize_produces_valid_json():
    project = _base_project()
    result = serialize_project(project)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_serialize_preserves_id():
    project = _base_project()
    raw = serialize_project(project)
    data = json.loads(raw)
    assert str(project.id) == data["id"]


def test_serialize_preserves_title():
    project = _base_project(title="My Study")
    data = json.loads(serialize_project(project))
    assert data["title"] == "My Study"


def test_serialize_preserves_idea():
    project = _base_project(idea="Unique idea text.")
    data = json.loads(serialize_project(project))
    assert data["idea"] == "Unique idea text."


def test_serialize_preserves_state():
    project = _base_project(state=ResearchState.QUESTION_DEFINED)
    data = json.loads(serialize_project(project))
    assert data["state"] == "QUESTION_DEFINED"


def test_serialize_preserves_research_question():
    project = _base_project(
        research_question=ResearchQuestion(text="Does X reduce Y?")
    )
    data = json.loads(serialize_project(project))
    assert data["research_question"]["text"] == "Does X reduce Y?"


def test_serialize_preserves_framework_type():
    project = _base_project(
        framework=ResearchFramework(type=FrameworkType.PICO)
    )
    data = json.loads(serialize_project(project))
    assert data["framework"]["type"] == "PICO"


def test_serialize_preserves_framework_components():
    project = _full_project()
    data = json.loads(serialize_project(project))
    assert data["framework"]["population"]["description"] == "Adults over 65"
    assert data["framework"]["intervention"]["description"] == "Drug A"
    assert data["framework"]["comparator"]["description"] == "Placebo"
    assert data["framework"]["outcome"]["description"] == "All-cause mortality"


def test_serialize_preserves_tasks():
    project = _full_project()
    data = json.loads(serialize_project(project))
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["title"] == "Define population"
    assert data["tasks"][0]["status"] == "TODO"
    assert data["tasks"][0]["priority"] == "HIGH"
    assert data["tasks"][0]["origin"] == "SYSTEM"


def test_serialize_preserves_transition_history():
    project = _full_project()
    data = json.loads(serialize_project(project))
    assert len(data["transition_history"]) == 1
    rec = data["transition_history"][0]
    assert rec["from_state"] == "IDEA"
    assert rec["to_state"] == "QUESTION_DEFINED"
    assert rec["actor"] == "RESEARCHER"
    assert rec["reason"] == "Researcher confirmed."


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------

def test_deserialize_returns_research_project():
    project = _base_project()
    raw = serialize_project(project)
    restored = deserialize_project(raw)
    assert isinstance(restored, ResearchProject)


def test_deserialize_invalid_data_raises():
    with pytest.raises(Exception):
        deserialize_project('{"title": "missing required fields"}')


def test_deserialize_garbage_raises():
    with pytest.raises(Exception):
        deserialize_project("not json at all")


def test_deserialize_empty_string_raises():
    with pytest.raises(Exception):
        deserialize_project("")


# ---------------------------------------------------------------------------
# Round-trip integrity
# ---------------------------------------------------------------------------

def test_round_trip_preserves_id():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.id == project.id


def test_round_trip_preserves_title():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.title == project.title


def test_round_trip_preserves_idea():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.idea == project.idea


def test_round_trip_preserves_state():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.state == project.state
    assert isinstance(restored.state, ResearchState)


def test_round_trip_preserves_research_question():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.research_question is not None
    assert restored.research_question.text == project.research_question.text


def test_round_trip_preserves_framework():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.framework is not None
    assert restored.framework.type == FrameworkType.PICO
    assert restored.framework.population.description == "Adults over 65"
    assert restored.framework.intervention.description == "Drug A"
    assert restored.framework.comparator.description == "Placebo"
    assert restored.framework.outcome.description == "All-cause mortality"


def test_round_trip_preserves_tasks():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert len(restored.tasks) == 1
    task = restored.tasks[0]
    assert task.title == "Define population"
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH
    assert task.origin == ActorType.SYSTEM


def test_round_trip_preserves_transition_history():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert len(restored.transition_history) == 1
    rec = restored.transition_history[0]
    assert rec.from_state == ResearchState.IDEA
    assert rec.to_state == ResearchState.QUESTION_DEFINED
    assert rec.actor == ActorType.RESEARCHER
    assert rec.reason == "Researcher confirmed."


def test_round_trip_framework_is_complete():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.framework.is_complete is True


def test_round_trip_none_question_preserved():
    project = _base_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.research_question is None


def test_round_trip_none_framework_preserved():
    project = _base_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.framework is None


def test_round_trip_empty_tasks_preserved():
    project = _base_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.tasks == []


def test_round_trip_empty_history_preserved():
    project = _base_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.transition_history == []


def test_round_trip_timestamps_preserved():
    project = _full_project()
    restored = deserialize_project(serialize_project(project))
    assert restored.transition_history[0].timestamp == project.transition_history[0].timestamp


# ---------------------------------------------------------------------------
# InMemoryProjectRepository — basic operations
# ---------------------------------------------------------------------------

def test_empty_repository_get_returns_none():
    repo = InMemoryProjectRepository()
    assert repo.get(uuid4()) is None


def test_empty_repository_exists_returns_false():
    repo = InMemoryProjectRepository()
    assert repo.exists(uuid4()) is False


def test_save_and_get_project():
    repo = InMemoryProjectRepository()
    project = _base_project()
    repo.save(project)
    retrieved = repo.get(project.id)
    assert retrieved is not None
    assert retrieved.id == project.id


def test_exists_returns_true_after_save():
    repo = InMemoryProjectRepository()
    project = _base_project()
    repo.save(project)
    assert repo.exists(project.id) is True


def test_get_missing_project_returns_none():
    repo = InMemoryProjectRepository()
    assert repo.get(uuid4()) is None


def test_delete_removes_project():
    repo = InMemoryProjectRepository()
    project = _base_project()
    repo.save(project)
    repo.delete(project.id)
    assert repo.get(project.id) is None
    assert repo.exists(project.id) is False


def test_delete_missing_project_is_safe():
    repo = InMemoryProjectRepository()
    repo.delete(uuid4())  # must not raise


def test_save_replaces_existing_project():
    repo = InMemoryProjectRepository()
    project = _base_project(title="Original")
    repo.save(project)

    updated = ResearchProject(
        id=project.id,
        title="Updated",
        idea="Same idea.",
        state=ResearchState.QUESTION_DEFINED,
    )
    repo.save(updated)

    retrieved = repo.get(project.id)
    assert retrieved.title == "Updated"
    assert retrieved.state == ResearchState.QUESTION_DEFINED


def test_repository_does_not_modify_project_domain_data():
    repo = InMemoryProjectRepository()
    project = _base_project(title="Unchanged")
    repo.save(project)
    assert project.title == "Unchanged"
    assert project.state == ResearchState.IDEA


# ---------------------------------------------------------------------------
# Isolation — mutations on retrieved project must not affect stored copy
# ---------------------------------------------------------------------------

def test_mutating_retrieved_project_does_not_affect_stored():
    repo = InMemoryProjectRepository()
    project = _base_project()
    repo.save(project)

    retrieved = repo.get(project.id)
    retrieved.state = ResearchState.QUESTION_DEFINED
    retrieved.tasks.append(
        ResearchTask(
            title="Extra",
            reason="Extra.",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            origin=ActorType.SYSTEM,
        )
    )

    stored_again = repo.get(project.id)
    assert stored_again.state == ResearchState.IDEA
    assert stored_again.tasks == []


def test_mutating_original_after_save_does_not_affect_stored():
    repo = InMemoryProjectRepository()
    project = _base_project()
    repo.save(project)

    project.state = ResearchState.QUESTION_DEFINED

    stored = repo.get(project.id)
    assert stored.state == ResearchState.IDEA
