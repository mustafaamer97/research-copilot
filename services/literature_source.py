"""Canonical literature source adapter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from domain.literature import ExternalSource, LiteratureRecord
from domain.literature_search import LiteratureSearchStrategy
from domain.research_article import ResearchArticle


# ---------------------------------------------------------------------------
# Canonical exception
# ---------------------------------------------------------------------------


class LiteratureSourceError(Exception):
    """Canonical exception for literature source retrieval failures."""

    def __init__(self, source: ExternalSource, message: str) -> None:
        self.source = source
        self.message = message
        super().__init__(f"[{source.value}] {message}")


# ---------------------------------------------------------------------------
# Search result
# ---------------------------------------------------------------------------


class LiteratureSearchResult(BaseModel):
    """
    Canonical normalized result returned by every literature adapter.

    Adapter implementations may still construct the legacy
    LiteratureRecord internally. At this boundary, all records are
    normalized into the unified ResearchArticle model.

    This allows PubMed, Europe PMC, OpenAlex, and future providers to
    expose one stable domain contract to the rest of the application.
    """

    model_config = {"frozen": True}

    source: ExternalSource
    records: list[ResearchArticle] = Field(default_factory=list)
    retrieved_at: datetime
    query: str

    @model_validator(mode="before")
    @classmethod
    def normalize_records(cls, values):
        """
        Normalize legacy LiteratureRecord instances into ResearchArticle.

        This compatibility bridge intentionally lives at the service
        boundary so existing adapters do not need to be rewritten all at
        once.
        """
        if not isinstance(values, dict):
            return values

        records = values.get("records", [])

        normalized: list[ResearchArticle] = []

        for record in records:
            if isinstance(record, ResearchArticle):
                normalized.append(record)
                continue

            if isinstance(record, LiteratureRecord):
                normalized.append(
                    ResearchArticle(
                        id=record.id,
                        title=record.title,
                        authors=list(record.authors),
                        journal=record.journal,
                        publication_date=record.publication_date,
                        abstract=record.abstract,
                        doi=record.doi,
                        pmid=record.pmid,
                        source=record.source.value,
                        source_record_id=record.source_record_id,
                        url=record.source_url,
                        retrieved_at=record.retrieved_at,
                    )
                )
                continue

            raise TypeError(
                "LiteratureSearchResult.records must contain "
                "ResearchArticle or LiteratureRecord instances."
            )

        values["records"] = normalized
        return values

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


# ---------------------------------------------------------------------------
# Abstract adapter contract
# ---------------------------------------------------------------------------


class LiteratureSourceAdapter(ABC):
    """
    Canonical interface for all external literature source adapters.

    Concrete adapters must implement search() and return a
    LiteratureSearchResult whose records are normalized ResearchArticle
    objects.

    The contract is independent of HTTP, provider SDKs, and network
    libraries.
    """

    @abstractmethod
    def search(
        self,
        strategy: LiteratureSearchStrategy,
    ) -> LiteratureSearchResult:
        """
        Execute a search against the external source.

        Requirements:
        - Must return LiteratureSearchResult.
        - Result records must be ResearchArticle objects.
        - Must raise LiteratureSourceError on retrieval failure.
        - Must never mutate the supplied strategy.
        """
        raise NotImplementedError
