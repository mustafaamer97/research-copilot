"""Tests for the Missing Information Engine."""
import pytest

from domain.framework import (
    Comparator,
    Exposure,
    FrameworkType,
    Intervention,
    Outcome,
    Population,
    ResearchFramework,
)
from domain.project import ResearchProject
from domain.research_question import ResearchQuestion
from domain.state import ResearchState
from services.framework_validator import (
    FrameworkValidationStatus,
    validate_framework,
)
from services.missing_information import (
    MissingInformation,
    MissingInformationPriority,
    get_missing_information,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project(**kwargs) -> ResearchProject:
    defaults = dict(title="Study", idea="An idea.")
    defaults.update(kwargs)
    return ResearchProject(**defaults)


def _complete_pico() -> ResearchFramework:
    return ResearchFramework(
        type=FrameworkType.PICO,
        
