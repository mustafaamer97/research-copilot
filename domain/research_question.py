"""Research question contract."""
from pydantic import BaseModel, field_validator


class ResearchQuestion(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Research question must not be empty or whitespace.")
        return v
