"""Deterministic study design recommendation engine."""
from pydantic import BaseModel

from domain.framework import FrameworkType
from domain.project import ResearchProject
from services.missing_information import get_missing_information

# ---------------------------------------------------------------------------
# Canonical design values
# ---------------------------------------------------------------------------

RCT = "Randomized Controlled Trial"
COHORT = "Cohort Study"
CASE_CONTROL = "Case-Control Study"
CROSS_SECTIONAL = "Cross-Sectional Study"
DIAGNOSTIC = "Diagnostic Study"

_STANDARD_LIMITATIONS = (
    "This recommendation does not establish feasibility, ethical approval, "
    "recruitment capability, allocation feasibility, temporal constraints, "
    "or causal validity in the actual research setting. "
    "Expert methodological review is required before proceeding."
)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

class StudyDesignRecommendation(BaseModel):
    recommended_design: str | None
    alternatives: list[str]
    rationale: str
    limitations: str
    needs_expert_review: bool = True


# ---------------------------------------------------------------------------
# Internal rules
# ---------------------------------------------------------------------------

def _insufficient(rationale: str) -> StudyDesignRecommendation:
    return StudyDesignRecommendation(
        recommended_design=None,
        alternatives=[],
        rationale=rationale,
        limitations=_STANDARD_LIMITATIONS,
        needs_expert_review=True,
    )


def _recommend_pico(project: ResearchProject) -> StudyDesignRecommendation:
    missing = get_missing_information(project)
    if missing:
        fields = ", ".join(m.field for m in missing)
        return _insufficient(
            f"The available project information is insufficient to make a "
            f"confident study design recommendation. "
            f"The following information is missing: {fields}."
        )
    return StudyDesignRecommendation(
        recommended_design=RCT,
        alternatives=[COHORT],
        rationale=(
            "The framework contains a defined intervention and comparator, "
            "so a randomized controlled trial is a plausible study design to consider. "
            "This recommendation is based solely on the structural presence of an "
            "intervention and comparator within a PICO framework and does not "
            "constitute a definitive design selection."
        ),
        limitations=_STANDARD_LIMITATIONS,
        needs_expert_review=True,
    )


def _recommend_peco(project: ResearchProject) -> StudyDesignRecommendation:
    missing = get_missing_information(project)
    if missing:
        fields = ", ".join(m.field for m in missing)
        return _insufficient(
            f"The available project information is insufficient to make a "
            f"confident study design recommendation. "
            f"The following information is missing: {fields}."
        )
    return StudyDesignRecommendation(
        recommended_design=COHORT,
        alternatives=[CASE_CONTROL],
        rationale=(
            "The framework represents an exposure rather than an assigned intervention. "
            "A cohort study is a plausible design to consider when prospectively "
            "following an exposed and unexposed population. "
            "A case-control study is an alternative when outcomes are rare or "
            "retrospective ascertainment is more practical. "
            "This recommendation does not claim that a cohort design is universally "
            "superior and does not constitute a definitive design selection."
        ),
        limitations=_STANDARD_LIMITATIONS,
        needs_expert_review=True,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recommend_study_design(project: ResearchProject) -> StudyDesignRecommendation:
    """
    Return a deterministic study design recommendation based solely on
    explicit project information.

    Never mutates the project.
    Never calls AI or external APIs.
    Always sets needs_expert_review=True.
    """
    if project.framework is None:
        return _insufficient(
            "The available project information is insufficient to make a "
            "confident study design recommendation. "
            "A research framework is missing."
        )

    if project.framework.type == FrameworkType.PICO:
        return _recommend_pico(project)

    if project.framework.type == FrameworkType.PECO:
        return _recommend_peco(project)

    return _insufficient(
        "The available project information is insufficient to make a "
        "confident study design recommendation. "
        "The framework type is not supported by the current recommendation rules."
    )
