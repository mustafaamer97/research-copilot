"""Gate engine — determines readiness to enter a target state."""
from enum import Enum

from pydantic import BaseModel

from domain.project import ResearchProject
from domain.state import ResearchState


class GateStatus(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


class GateResult(BaseModel):
    status: GateStatus
    target_state: ResearchState
    reasons: list[str]

    @property
    def passed(self) -> bool:
        return self.status == GateStatus.PASS


def _gate_question_defined(project: ResearchProject) -> GateResult:
    if project.research_question is not None:
        return GateResult(
            status=GateStatus.PASS,
            target_state=ResearchState.QUESTION_DEFINED,
            reasons=[],
        )
    return GateResult(
        status=GateStatus.BLOCKED,
        target_state=ResearchState.QUESTION_DEFINED,
        reasons=["Research question is missing."],
    )


def _gate_framework_defined(project: ResearchProject) -> GateResult:
    if project.framework is None:
        return GateResult(
            status=GateStatus.BLOCKED,
            target_state=ResearchState.FRAMEWORK_DEFINED,
            reasons=["Research framework is missing."],
        )
    if not project.framework.is_complete:
        return GateResult(
            status=GateStatus.BLOCKED,
            target_state=ResearchState.FRAMEWORK_DEFINED,
            reasons=["Research framework is incomplete."],
        )
    return GateResult(
        status=GateStatus.PASS,
        target_state=ResearchState.FRAMEWORK_DEFINED,
        reasons=[],
    )


def _gate_design_selected(project: ResearchProject) -> GateResult:
    return GateResult(
        status=GateStatus.BLOCKED,
        target_state=ResearchState.DESIGN_SELECTED,
        reasons=["Study design is not implemented yet."],
    )


_GATE_REGISTRY: dict = {
    ResearchState.QUESTION_DEFINED: _gate_question_defined,
    ResearchState.FRAMEWORK_DEFINED: _gate_framework_defined,
    ResearchState.DESIGN_SELECTED: _gate_design_selected,
}


def check_gate(project: ResearchProject, target_state: ResearchState) -> GateResult:
    gate_fn = _GATE_REGISTRY.get(target_state)
    if gate_fn is None:
        return GateResult(
            status=GateStatus.BLOCKED,
            target_state=target_state,
            reasons=[f"Gate for {target_state.value} is not implemented yet."],
        )
    return gate_fn(project)
