"""Tests for the Study Design Recommendation Engine."""
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
from services.study_design_recommender import (
    CASE_CONTROL,
    COHORT,
    DIAGNOSTIC,
    RCT,
    StudyDesignRecommendation,
    recommend_study_design,
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
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )


def _complete_peco() -> ResearchFramework:
    return ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        exposure=Exposure(description="Smoking"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer"),
    )


def _pico_project(framework: ResearchFramework | None = None) -> ResearchProject:
    return _project(
        state=ResearchState.QUESTION_DEFINED,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
        framework=framework or _complete_pico(),
    )


def _peco_project(framework: ResearchFramework | None = None) -> ResearchProject:
    return _project(
        state=ResearchState.QUESTION_DEFINED,
        research_question=ResearchQuestion(text="Does smoking cause lung cancer?"),
        framework=framework or _complete_peco(),
    )


# ---------------------------------------------------------------------------
# PICO — complete
# ---------------------------------------------------------------------------

def test_complete_pico_recommends_rct():
    rec = recommend_study_design(_pico_project())
    assert rec.recommended_design == RCT


def test_complete_pico_alternative_is_cohort():
    rec = recommend_study_design(_pico_project())
    assert COHORT in rec.alternatives


def test_complete_pico_needs_expert_review():
    rec = recommend_study_design(_pico_project())
    assert rec.needs_expert_review is True


def test_complete_pico_has_rationale():
    rec = recommend_study_design(_pico_project())
    assert rec.rationale
    assert len(rec.rationale) > 0


def test_complete_pico_has_limitations():
    rec = recommend_study_design(_pico_project())
    assert rec.limitations
    assert len(rec.limitations) > 0


def test_complete_pico_rationale_mentions_intervention():
    rec = recommend_study_design(_pico_project())
    assert "intervention" in rec.rationale.lower()


def test_complete_pico_rationale_not_claiming_definitive():
    rec = recommend_study_design(_pico_project())
    lower = rec.rationale.lower()
    assert "definitive" not in lower or "not" in lower


# ---------------------------------------------------------------------------
# PICO — incomplete
# ---------------------------------------------------------------------------

def test_incomplete_pico_no_recommended_design():
    fw = ResearchFramework(type=FrameworkType.PICO)
    rec = recommend_study_design(_pico_project(framework=fw))
    assert rec.recommended_design is None


def test_incomplete_pico_no_alternatives():
    fw = ResearchFramework(type=FrameworkType.PICO)
    rec = recommend_study_design(_pico_project(framework=fw))
    assert rec.alternatives == []


def test_incomplete_pico_needs_expert_review():
    fw = ResearchFramework(type=FrameworkType.PICO)
    rec = recommend_study_design(_pico_project(framework=fw))
    assert rec.needs_expert_review is True


def test_incomplete_pico_rationale_mentions_insufficient():
    fw = ResearchFramework(type=FrameworkType.PICO)
    rec = recommend_study_design(_pico_project(framework=fw))
    assert "insufficient" in rec.rationale.lower()


def test_missing_comparator_prevents_pico_recommendation():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        outcome=Outcome(description="Mortality"),
    )
    rec = recommend_study_design(_pico_project(framework=fw))
    assert rec.recommended_design is None


def test_missing_outcome_prevents_pico_recommendation():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
    )
    rec = recommend_study_design(_pico_project(framework=fw))
    assert rec.recommended_design is None


def test_missing_population_prevents_pico_recommendation():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    rec = recommend_study_design(_pico_project(framework=fw))
    assert rec.recommended_design is None


def test_missing_intervention_prevents_pico_recommendation():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    rec = recommend_study_design(_pico_project(framework=fw))
    assert rec.recommended_design is None


# ---------------------------------------------------------------------------
# PECO — complete
# ---------------------------------------------------------------------------

def test_complete_peco_recommends_cohort():
    rec = recommend_study_design(_peco_project())
    assert rec.recommended_design == COHORT


def test_complete_peco_alternative_is_case_control():
    rec = recommend_study_design(_peco_project())
    assert CASE_CONTROL in rec.alternatives


def test_complete_peco_needs_expert_review():
    rec = recommend_study_design(_peco_project())
    assert rec.needs_expert_review is True


def test_complete_peco_has_rationale():
    rec = recommend_study_design(_peco_project())
    assert rec.rationale
    assert len(rec.rationale) > 0


def test_complete_peco_rationale_mentions_exposure():
    rec = recommend_study_design(_peco_project())
    assert "exposure" in rec.rationale.lower()


def test_complete_peco_rationale_does_not_claim_cohort_universally_superior():
    rec = recommend_study_design(_peco_project())
    lower = rec.rationale.lower()
    assert "universally superior" not in lower


# ---------------------------------------------------------------------------
# PECO — incomplete
# ---------------------------------------------------------------------------

def test_incomplete_peco_no_recommended_design():
    fw = ResearchFramework(type=FrameworkType.PECO)
    rec = recommend_study_design(_peco_project(framework=fw))
    assert rec.recommended_design is None


def test_incomplete_peco_no_alternatives():
    fw = ResearchFramework(type=FrameworkType.PECO)
    rec = recommend_study_design(_peco_project(framework=fw))
    assert rec.alternatives == []


def test_incomplete_peco_needs_expert_review():
    fw = ResearchFramework(type=FrameworkType.PECO)
    rec = recommend_study_design(_peco_project(framework=fw))
    assert rec.needs_expert_review is True


def test_incomplete_peco_rationale_mentions_insufficient():
    fw = ResearchFramework(type=FrameworkType.PECO)
    rec = recommend_study_design(_peco_project(framework=fw))
    assert "insufficient" in rec.rationale.lower()


# ---------------------------------------------------------------------------
# No framework
# ---------------------------------------------------------------------------

def test_no_framework_returns_no_design():
    project = _project(state=ResearchState.IDEA)
    rec = recommend_study_design(project)
    assert rec.recommended_design is None


def test_no_framework_needs_expert_review():
    project = _project(state=ResearchState.IDEA)
    rec = recommend_study_design(project)
    assert rec.needs_expert_review is True


def test_no_framework_rationale_mentions_insufficient():
    project = _project(state=ResearchState.IDEA)
    rec = recommend_study_design(project)
    assert "insufficient" in rec.rationale.lower()


# ---------------------------------------------------------------------------
# No unsupported design inferred
# ---------------------------------------------------------------------------

def test_diagnostic_study_not_inferred_from_pico():
    rec = recommend_study_design(_pico_project())
    assert rec.recommended_design != DIAGNOSTIC
    assert DIAGNOSTIC not in rec.alternatives


def test_diagnostic_study_not_inferred_from_peco():
    rec = recommend_study_design(_peco_project())
    assert rec.recommended_design != DIAGNOSTIC
    assert DIAGNOSTIC not in rec.alternatives


def test_cross_sectional_not_inferred_from_pico():
    from services.study_design_recommender import CROSS_SECTIONAL
    rec = recommend_study_design(_pico_project())
    assert rec.recommended_design != CROSS_SECTIONAL
    assert CROSS_SECTIONAL not in rec.alternatives


def test_cross_sectional_not_inferred_from_peco():
    from services.study_design_recommender import CROSS_SECTIONAL
    rec = recommend_study_design(_peco_project())
    assert rec.recommended_design != CROSS_SECTIONAL
    assert CROSS_SECTIONAL not in rec.alternatives


# ---------------------------------------------------------------------------
# Integrity — no mutation
# ---------------------------------------------------------------------------

def test_recommendation_does_not_modify_project_state():
    project = _pico_project()
    original_state = project.state
    recommend_study_design(project)
    assert project.state == original_state


def test_recommendation_does_not_modify_project_framework():
    project = _pico_project()
    original_type = project.framework.type
    recommend_study_design(project)
    assert project.framework.type == original_type


def test_recommendation_does_not_modify_framework_components():
    project = _pico_project()
    original_population = project.framework.population.description
    recommend_study_design(project)
    assert project.framework.population.description == original_population


def test_recommendation_does_not_create_transition_record():
    project = _pico_project()
    original_history_len = len(project.transition_history)
    recommend_study_design(project)
    assert len(project.transition_history) == original_history_len


def test_recommendation_does_not_modify_tasks():
    project = _pico_project()
    original_task_count = len(project.tasks)
    recommend_study_design(project)
    assert len(project.tasks) == original_task_count


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_recommendation_is_deterministic_pico():
    project = _pico_project()
    r1 = recommend_study_design(project)
    r2 = recommend_study_design(project)
    assert r1.recommended_design == r2.recommended_design
    assert r1.alternatives == r2.alternatives
    assert r1.rationale == r2.rationale


def test_recommendation_is_deterministic_peco():
    project = _peco_project()
    r1 = recommend_study_design(project)
    r2 = recommend_study_design(project)
    assert r1.recommended_design == r2.recommended_design
    assert r1.alternatives == r2.alternatives
    assert r1.rationale == r2.rationale


def test_recommendation_is_deterministic_incomplete():
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _pico_project(framework=fw)
    r1 = recommend_study_design(project)
    r2 = recommend_study_design(project)
    assert r1.recommended_design == r2.recommended_design
    assert r1.rationale == r2.rationale


# ---------------------------------------------------------------------------
# Result model integrity
# ---------------------------------------------------------------------------

def test_result_is_pydantic_model():
    rec = recommend_study_design(_pico_project())
    assert isinstance(rec, StudyDesignRecommendation)


def test_needs_expert_review_always_true_pico():
    assert recommend_study_design(_pico_project()).needs_expert_review is True


def test_needs_expert_review_always_true_peco():
    assert recommend_study_design(_peco_project()).needs_expert_review is True


def test_needs_expert_review_always_true_incomplete():
    fw = ResearchFramework(type=FrameworkType.PICO)
    assert recommend_study_design(_pico_project(framework=fw)).needs_expert_review is True


def test_needs_expert_review_always_true_no_framework():
    assert recommend_study_design(_project()).needs_expert_review is True


def test_limitations_always_present_complete():
    rec = recommend_study_design(_pico_project())
    assert rec.limitations
    assert "feasibility" in rec.limitations.lower()


def test_limitations_always_present_incomplete():
    fw = ResearchFramework(type=FrameworkType.PICO)
    rec = recommend_study_design(_pico_project(framework=fw))
    assert rec.limitations


# ---------------------------------------------------------------------------
# Public import
# ---------------------------------------------------------------------------

def test_recommend_study_design_importable_from_services():
    from services import recommend_study_design as fn
    assert callable(fn)


def test_study_design_recommendation_importable_from_services():
    from services import StudyDesignRecommendation
    assert StudyDesignRecommendation is not None
