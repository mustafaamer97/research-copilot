"""Canonical literature source adapter contract."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator

from domain.literature import ExternalSource, LiteratureRecord
from domain.literature_search import LiteratureSearchStrategy


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
    model_config = {"frozen": True}

    source: ExternalSource
    records: list[LiteratureRecord] = Field(default_factory=list)
    retrieved_at: datetime
    query: str

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("retrieved_at must be timezone-aware (UTC required).")
        return v


# ---------------------------------------------------------------------------
# Abstract adapter contract
# ---------------------------------------------------------------------------

class LiteratureSourceAdapter(ABC):
    """
    Canonical interface for all external literature source adapters.

    Concrete adapters must implement search() and return
    a LiteratureSearchResult.  The contract is independent of HTTP,
    provider SDKs, and network libraries.
    """

    @abstractmethod
    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        """
        Execute a search against the external source using the supplied strategy.

        Must return a LiteratureSearchResult.
        Must raise LiteratureSourceError on retrieval failure.
        Must never mutate the supplied strategy.
        """
