"""Task Engine — converts missing research requirements into actionable tasks."""
from domain.actors import ActorType
from domain.framework import FrameworkType
from domain.project import ResearchProject
from domain.state import ResearchState
from domain.task import ResearchTask, TaskPriority, TaskStatus


def _already_has_active_task(project: ResearchProject, title: str) -> bool:
    """Return True if an equivalent TODO or IN_PROGRESS task already exists."""
    for task in project.tasks:
        if task.title == title and task.status in (
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
        ):
            return True
    return False


def _make_task(title: str, reason: str) -> ResearchTask:
    return ResearchTask(
        title=title,
        reason=reason,
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        origin=ActorType.SYSTEM,
    )


# ---------------------------------------------------------------------------
# Rule 1 — missing research question
# ---------------------------------------------------------------------------

def _tasks_for_idea(project: ResearchProject) -> list[ResearchTask]:
    tasks: list[ResearchTask] = []
    if project.research_question is None:
        title = "Define research question"
        if not _already_has_active_task(project, title):
            tasks.append(
                _make_task(
                    title=title,
                    reason=(
                        "A research question is required before the project "
                        "can move to QUESTION_DEFINED."
                    ),
                )
            )
    return tasks


# ---------------------------------------------------------------------------
# Rule 2 & 3 — missing or incomplete framework
# ---------------------------------------------------------------------------

_PICO_COMPONENTS = ["population", "intervention", "comparator", "outcome"]
_PECO_COMPONENTS = ["population", "exposure", "comparator", "outcome"]

_COMPONENT_TITLES: dict[str, str] = {
    "population": "Define population",
    "intervention": "Define intervention",
    "exposure": "Define exposure",
    "comparator": "Define comparator",
    "outcome": "Define primary outcome",
}

_COMPONENT_REASONS: dict[str, str] = {
    "population": (
        "The research framework is incomplete because the required population is missing."
    ),
    "intervention": (
        "The research framework is incomplete because the required intervention is missing."
    ),
    "exposure": (
        "The research framework is incomplete because the required exposure is missing."
    ),
    "comparator": (
        "The research framework is incomplete because the required comparator is missing."
    ),
    "outcome": (
        "The research framework is incomplete because the required outcome is missing."
    ),
}


def _tasks_for_question_defined(project: ResearchProject) -> list[ResearchTask]:
    tasks: list[ResearchTask] = []

    if project.framework is None:
        title = "Define research framework"
        if not _already_has_active_task(project, title):
            tasks.append(
                _make_task(
                    title=title,
                    reason=(
                        "A complete research framework is required before the project "
                        "can move to FRAMEWORK_DEFINED."
                    ),
                )
            )
        return tasks

    if project.framework.is_complete:
        return tasks

    if project.framework.type == FrameworkType.PICO:
        required = _PICO_COMPONENTS
    else:
        required = _PECO_COMPONENTS

    for component in required:
        if getattr(project.framework, component) is None:
            title = _COMPONENT_TITLES[component]
            if not _already_has_active_task(project, title):
                tasks.append(_make_task(title=title, reason=_COMPONENT_REASONS[component]))

    return tasks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_RULE_MAP = {
    ResearchState.IDEA: _tasks_for_idea,
    ResearchState.QUESTION_DEFINED: _tasks_for_question_defined,
}


def generate_tasks_for_project(project: ResearchProject) -> list[ResearchTask]:
    """
    Return a list of tasks representing unresolved requirements.

    Does NOT mutate project.tasks.
    """
    rule_fn = _RULE_MAP.get(project.state)
    if rule_fn is None:
        return []
    return rule_fn(project)
