from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EvidenceExtraction(BaseModel):
    """
    Canonical evidence extraction record.

    One extraction record belongs to one included article.
    """

    model_config = {"frozen": True}

    id: UUID = Field(default_factory=uuid4)

    article_id: UUID

    population: str | None = None

    intervention: str | None = None

    comparator: str | None = None

    outcome: str | None = None

    study_design: str | None = None

    risk_of_bias: str | None = None

    notes: str | None = None

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
