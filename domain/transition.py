"""Transition record contract."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from domain.actors import ActorType
from domain.state import ResearchState


class TransitionRecord(BaseModel):
    model_config = {"frozen": True}

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    from_state: ResearchState
    to_state: ResearchState
    actor: ActorType
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reason: str
