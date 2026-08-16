"""Deterministic next action engine."""
from enum import Enum

from pydantic import BaseModel

from domain.project import ResearchProject
from domain.state import ResearchState
from services.missing_information import get_missing_information


class NextActionPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NextAction(BaseModel):
    action: str
    reason: str
    priority: NextActionPriority
    blocked: bool = False


# ---------------------------------------------------------------------------
# Internal rule handlers
# ---------------------------------------------------------------------------

def _handle_idea(project: ResearchProject) -> NextAction:
    if project.research_question is None:
        return NextAction(
            action="Define research question",
            reason=(
                "A research question is required before the research framework "
                "can be completed."
            ),
            priority=NextActionPriority.HIGH,
            blocked=False,
        )
    return NextAction(
        action="Define research framework",
        reason=(
            "The research question exists, but the research framework "
            "has not been defined."
        ),
        priority=NextActionPriority.HIGH,
        blocked=False,
    )


def _handle_question_defined(project: ResearchProject) -> NextAction:
    if project.framework is None:
        return NextAction(
            action="Define research framework",
            reason=(
                "A research framework is required before the study design "
                "can be selected."
            ),
            priority=NextActionPriority.HIGH,
            blocked=False,
        )

    missing = get_missing_information(project)
    if missing:
        first = missing[0]
        return NextAction(
            action=f"Define {first.field}",
            reason=f"{first.field} is required to complete the research framework.",
            priority=NextActionPriority.HIGH,
            blocked=False,
        )

    return NextAction(
        action="Review study design recommendation",
        reason=(
            "The research framework is complete and a study design recommendation "
            "is available for researcher review."
        ),
        priority=NextActionPriority.HIGH,
        blocked=False,
    )


def _handle_framework_defined(project: ResearchProject) -> NextAction:
    return NextAction(
        action="Select study design",
        reason=(
            "The research framework is complete and the study design must be "
            "selected by the researcher."
        ),
        priority=NextActionPriority.HIGH,
        blocked=False,
    )


def _handle_design_selected(project: ResearchProject) -> NextAction:
    return NextAction(
        action="Prepare research protocol",
        reason=(
            "The study design has been selected and the next lifecycle stage "
            "is protocol preparation."
        ),
        priority=NextActionPriority.HIGH,
        blocked=False,
    )


def _handle_future(project: ResearchProject) -> NextAction:
    return NextAction(
        action="Continue research workflow",
        reason=(
            "The next workflow intelligence for this research state has not "
            "been implemented yet."
        ),
        priority=NextActionPriority.LOW,
        blocked=False,
    )


# ---------------------------------------------------------------------------
# Dispatch map
# ---------------------------------------------------------------------------

_HANDLERS = {
    ResearchState.IDEA: _handle_idea,
    ResearchState.QUESTION_DEFINED: _handle_question_defined,
    ResearchState.FRAMEWORK_DEFINED: _handle_framework_defined,
    ResearchState.DESIGN_SELECTED: _handle_design_selected,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_next_action(project: ResearchProject) -> NextAction:
    """
    Return a deterministic next action for the current project state.

    Never mutates the project.
    Never calls AI or external APIs.
    """
    handler = _HANDLERS.get(project.state, _handle_future)
    return handler(project)
