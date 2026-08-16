"""Tests for ResearchTask."""
from domain.actors import ActorType
from domain.task import ResearchTask, TaskPriority, TaskStatus


def test_all_statuses_exist():
    values = {s.value for s in TaskStatus}
    assert values == {"TODO", "IN_PROGRESS", "COMPLETED", "BLOCKED"}


def test_all_priorities_exist():
    values = {p.value for p in TaskPriority}
    assert values == {"LOW", "MEDIUM", "HIGH"}


def test_task_creation_defaults():
    task = ResearchTask(
        title="Define research question",
        reason="Required for next stage",
        origin=ActorType.SYSTEM,
    )
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.MEDIUM
    assert task.origin == ActorType.SYSTEM
    assert task.id is not None
    assert task.created_at is not None


def test_task_origin_uses_actor_type():
    for actor in ActorType:
        task = ResearchTask(
            title="Task",
            reason="Reason",
            origin=actor,
        )
        assert task.origin == actor


def test_task_explicit_status_and_priority():
    task = ResearchTask(
        title="Collect data",
        reason="Data phase",
        origin=ActorType.RESEARCHER,
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
    )
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.priority == TaskPriority.HIGH


def test_task_has_no_execution_logic():
    task = ResearchTask(
        title="Task",
        reason="Reason",
        origin=ActorType.AI,
    )
    assert not callable(getattr(task, "execute", None))
    assert not callable(getattr(task, "run", None))
