"""StateManager — sole authority for lifecycle transitions."""
from datetime import datetime, timezone
from uuid import uuid4

from domain.actors import ActorType
from domain.project import ResearchProject
from domain.state import ResearchState
from domain.transition import TransitionRecord
from state_machine.gates import GateStatus, check_gate
from state_machine.transitions import is_transition_allowed

_DEFAULT_REASON = "State transition executed."


class InvalidTransitionError(Exception):
    """Raised when the requested transition is not structurally allowed."""

    def __init__(self, from_state: ResearchState, to_state: ResearchState) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Transition from {from_state.value} to {to_state.value} is not allowed."
        )


class GateBlockedError(Exception):
    """Raised when the gate for the target state is blocked."""

    def __init__(self, target_state: ResearchState, reasons: list[str]) -> None:
        self.target_state = target_state
        self.reasons = reasons
        super().__init__(
            f"Gate blocked for {target_state.value}: {'; '.join(reasons)}"
        )


class StateManager:
    def transition(
        self,
        project: ResearchProject,
        target_state: ResearchState,
        actor: ActorType,
        reason: str | None = None,
    ) -> TransitionRecord:
        from_state = project.state

        if not is_transition_allowed(from_state, target_state):
            raise InvalidTransitionError(from_state, target_state)

        gate_result = check_gate(project, target_state)
        if gate_result.status != GateStatus.PASS:
            raise GateBlockedError(target_state, gate_result.reasons)

        record = TransitionRecord(
            id=uuid4(),
            project_id=project.id,
            from_state=from_state,
            to_state=target_state,
            actor=actor,
            timestamp=datetime.now(timezone.utc),
            reason=reason if reason is not None else _DEFAULT_REASON,
        )

        project.state = target_state
        project.transition_history.append(record)

        return record
