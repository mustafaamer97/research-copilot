from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RiskOfBias(str, Enum):
    LOW = "Low"
    SOME_CONCERNS = "Some Concerns"
    HIGH = "High"


class EvidenceExtraction(BaseModel):

    model_config = {"frozen": True}

    id: UUID = Field(default_factory=uuid4)

    article_id: UUID

    doi: str | None = None
    pmid: str | None = None

    population: str | None = None

    intervention: str | None = None

    comparator: str | None = None

    outcome: str | None = None

    study_design: str | None = None

    risk_of_bias: RiskOfBias | None = None

    notes: str | None = None

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
