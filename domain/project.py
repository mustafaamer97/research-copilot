"""ResearchProject aggregate root."""
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from domain.framework import ResearchFramework
from domain.research_question import ResearchQuestion
from domain.state import ResearchState
from domain.task import ResearchTask
from domain.transition import TransitionRecord


class ResearchProject(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    idea: str
    state: ResearchState = ResearchState.IDEA
    research_question: ResearchQuestion | None = None
    framework: ResearchFramework | None = None
    tasks: list[ResearchTask] = Field(default_factory=list)
    transition_history: list[TransitionRecord] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title must not be empty or whitespace.")
        return v

    @field_validator("idea")
    @classmethod
    def idea_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Idea must not be empty or whitespace.")
        return v
