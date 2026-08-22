"""
Unified research article domain contract.

ResearchArticle is the canonical article representation used by the
Research Copilot across all literature sources.

Provider-specific adapters may have different response formats, but the
application domain must work with this single normalized model.

No AI.
No external API.
No provider-specific logic.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ResearchArticleSource(str, Enum):
    """Supported external literature sources."""

    PUBMED = "PUBMED"
    EUROPE_PMC = "EUROPE_PMC"
    OPENALEX = "OPENALEX"
    CROSSREF = "CROSSREF"


class ResearchArticle(BaseModel):
    """
    Canonical representation of one scientific article.

    All external literature adapters must eventually normalize their
    provider-specific records into this model.

    The model deliberately contains only article-level information.
    Search strategy, screening decisions, evidence assessment, and
    researcher decisions belong to separate domain objects.
    """

    model_config = {"frozen": True}

    # Stable application-level identity.
    id: UUID = Field(default_factory=uuid4)

    # Core bibliographic information.
    title: str
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    publication_date: str | None = None
    abstract: str | None = None

    # Persistent identifiers.
    doi: str | None = None
    pmid: str | None = None

    # Source provenance.
    source: ResearchArticleSource
    source_record_id: str
    url: str | None = None

    # Optional normalized research metadata.
    study_type: str | None = None
    keywords: list[str] = Field(default_factory=list)

    # Retrieval metadata.
    retrieved_at: datetime

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("title must not be empty or whitespace.")
        return value.strip()

    @field_validator("source_record_id")
    @classmethod
    def source_record_id_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError(
                "source_record_id must not be empty or whitespace."
            )
        return value.strip()

    @field_validator("authors")
    @classmethod
    def authors_must_not_contain_blank_values(
        cls,
        value: list[str],
    ) -> list[str]:
        return [
            author.strip()
            for author in value
            if isinstance(author, str) and author.strip()
        ]

    @field_validator("keywords")
    @classmethod
    def keywords_must_not_contain_blank_values(
        cls,
        value: list[str],
    ) -> list[str]:
        return [
            keyword.strip()
            for keyword in value
            if isinstance(keyword, str) and keyword.strip()
        ]

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_must_be_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(
                "retrieved_at must be timezone-aware (UTC required)."
            )
        return value

    # ------------------------------------------------------------------
    # Compatibility / provenance helpers
    # ------------------------------------------------------------------

    @property
    def source_url(self) -> str | None:
        """
        Backward-compatible access to the canonical article URL.

        Older LiteratureRecord consumers use `source_url`.
        The unified model uses `url`.
        """
        return self.url
