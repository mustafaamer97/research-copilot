"""Deterministic missing information engine."""
from enum import Enum

from pydantic import BaseModel

from domain.project import ResearchProject
from domain.state import ResearchState
from services.framework_validator import FrameworkValidationStatus, validate_framework


class MissingInformationPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MissingInformation(BaseModel):
    field: str
    reason: str
    priority: MissingInformationPriority = MissingInformationPriority.HIGH


# ---------------------------------------------------------------------------
# Internal rule handlers
# ---------------------------------------------------------------------------

def _check_idea(project: ResearchProject) -> list[MissingInformation]:
    if project.research_question is None:
        return [
            MissingInformation(
                field="research_question",
                reason="Research question is missing.",
                priority=MissingInformationPriority.HIGH,
            )
        ]
    return []


def _check_question_defined(project: ResearchProject) -> list[MissingInformation]:
    if project.framework is None:
        return [
            MissingInformation(
                field="framework",
                reason="Research framework is missing.",
                priority=MissingInformationPriority.HIGH,
            )
        ]

    result = validate_framework(project.framework)
    if result.status == FrameworkValidationStatus.COMPLETE:
        return []

    return [
        MissingInformation(
            field=component,
            reason=f"{component} is missing.",
            priority=MissingInformationPriority.HIGH,
        )
        for component in result.missing_components
    ]


_RULE_MAP = {
    ResearchState.IDEA: _check_idea,
    ResearchState.QUESTION_DEFINED: _check_question_defined,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_missing_information(project: ResearchProject) -> list[MissingInformation]:
    """
    Return a deterministic list of missing information items for the project.

    Never mutates the project.
    Never invents information.
    Returns [] for states without implemented rules.
    """
    rule_fn = _RULE_MAP.get(project.state)
    if rule_fn is None:
        return []
    return rule_fn(project)
