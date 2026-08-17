"""Literature domain contracts."""
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ExternalSource(str, Enum):
    PUBMED = "PUBMED"
    EUROPE_PMC = "EUROPE_PMC"
    OPENALEX = "OPENALEX"
    CROSSREF = "CROSSREF"


class LiteratureRecord(BaseModel):
    model_config = {"frozen": True}

    id: UUID = Field(default_factory=uuid4)
    title: str
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    publication_date: str | None = None
    abstract: str | None = None
    doi: str | None = None
    pmid: str | None = None
    source: ExternalSource
    source_record_id: str
    source_url: str | None = None
    retrieved_at: datetime

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title must not be empty or whitespace.")
        return v

    @field_validator("source_record_id")
    @classmethod
    def source_record_id_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source_record_id must not be empty or whitespace.")
        return v

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("retrieved_at must be timezone-aware (UTC required).")
        return v
