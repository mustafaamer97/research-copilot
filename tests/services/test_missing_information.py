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


def _fields(items: list[MissingInformation]) -> list[str]:
    return [i.field for i in items]


# ---------------------------------------------------------------------------
# IDEA state
# ---------------------------------------------------------------------------

def test_idea_without_question_returns_research_question_missing():
    project = _project(state=ResearchState.IDEA)
    result = get_missing_information(project)
    assert len(result) == 1
    assert result[0].field == "research_question"


def test_idea_without_question_reason():
    project = _project(state=ResearchState.IDEA)
    result = get_missing_information(project)
    assert result[0].reason == "Research question is missing."


def test_idea_without_question_priority_high():
    project = _project(state=ResearchState.IDEA)
    result = get_missing_information(project)
    assert result[0].priority == MissingInformationPriority.HIGH


def test_idea_with_question_returns_empty():
    project = _project(
        state=ResearchState.IDEA,
        research_question=ResearchQuestion(text="Does X reduce Y?"),
    )
    result = get_missing_information(project)
    assert result == []


# ---------------------------------------------------------------------------
# QUESTION_DEFINED — missing framework
# ---------------------------------------------------------------------------

def test_question_defined_without_framework_returns_framework_missing():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    result = get_missing_information(project)
    assert len(result) == 1
    assert result[0].field == "framework"


def test_question_defined_without_framework_reason():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    result = get_missing_information(project)
    assert result[0].reason == "Research framework is missing."


def test_question_defined_without_framework_priority_high():
    project = _project(state=ResearchState.QUESTION_DEFINED)
    result = get_missing_information(project)
    assert result[0].priority == MissingInformationPriority.HIGH


# ---------------------------------------------------------------------------
# QUESTION_DEFINED — complete PICO
# ---------------------------------------------------------------------------

def test_question_defined_with_complete_pico_returns_empty():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    result = get_missing_information(project)
    assert result == []


# ---------------------------------------------------------------------------
# PICO — individual missing components
# ---------------------------------------------------------------------------

def test_pico_missing_population():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Population" in fields
    assert len(fields) == 1


def test_pico_missing_intervention():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Intervention" in fields
    assert len(fields) == 1


def test_pico_missing_comparator():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        outcome=Outcome(description="Mortality"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Comparator" in fields
    assert len(fields) == 1


def test_pico_missing_outcome():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Outcome" in fields
    assert len(fields) == 1


def test_pico_multiple_missing_canonical_order():
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert fields == ["Population", "Intervention", "Comparator", "Outcome"]


def test_pico_missing_comparator_and_outcome_canonical_order():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert fields == ["Comparator", "Outcome"]


# ---------------------------------------------------------------------------
# PICO — Exposure never reported
# ---------------------------------------------------------------------------

def test_pico_never_reports_exposure_complete():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_pico(),
    )
    fields = _fields(get_missing_information(project))
    assert "Exposure" not in fields


def test_pico_never_reports_exposure_incomplete():
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Exposure" not in fields


# ---------------------------------------------------------------------------
# PECO — individual missing components
# ---------------------------------------------------------------------------

def test_peco_missing_population():
    fw = ResearchFramework(
        type=FrameworkType.PECO,
        exposure=Exposure(description="Smoking"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Population" in fields
    assert len(fields) == 1


def test_peco_missing_exposure():
    fw = ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Exposure" in fields
    assert len(fields) == 1


def test_peco_missing_comparator():
    fw = ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        exposure=Exposure(description="Smoking"),
        outcome=Outcome(description="Lung cancer"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Comparator" in fields
    assert len(fields) == 1


def test_peco_missing_outcome():
    fw = ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        exposure=Exposure(description="Smoking"),
        comparator=Comparator(description="Non-smokers"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Outcome" in fields
    assert len(fields) == 1


def test_peco_multiple_missing_canonical_order():
    fw = ResearchFramework(type=FrameworkType.PECO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert fields == ["Population", "Exposure", "Comparator", "Outcome"]


def test_peco_missing_exposure_and_outcome_canonical_order():
    fw = ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        comparator=Comparator(description="Non-smokers"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert fields == ["Exposure", "Outcome"]


# ---------------------------------------------------------------------------
# PECO — Intervention never reported
# ---------------------------------------------------------------------------

def test_peco_never_reports_intervention_complete():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_peco(),
    )
    fields = _fields(get_missing_information(project))
    assert "Intervention" not in fields


def test_peco_never_reports_intervention_incomplete():
    fw = ResearchFramework(type=FrameworkType.PECO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "Intervention" not in fields


# ---------------------------------------------------------------------------
# No duplicate framework + component errors
# ---------------------------------------------------------------------------

def test_incomplete_framework_does_not_also_report_framework_field():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
    )
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    fields = _fields(get_missing_information(project))
    assert "framework" not in fields
    assert "Intervention" in fields


def test_complete_peco_does_not_report_framework_field():
    project = _project(
        state=ResearchState.QUESTION_DEFINED,
        framework=_complete_peco(),
    )
    fields = _fields(get_missing_information(project))
    assert "framework" not in fields


# ---------------------------------------------------------------------------
# Validator agreement
# ---------------------------------------------------------------------------

def test_missing_information_agrees_with_validator_complete_pico():
    fw = _complete_pico()
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    missing = get_missing_information(project)
    validator_result = validate_framework(fw)
    assert (missing == []) is (
        validator_result.status == FrameworkValidationStatus.COMPLETE
    )


def test_missing_information_agrees_with_validator_incomplete_pico():
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    missing = get_missing_information(project)
    validator_result = validate_framework(fw)
    assert len(missing) == len(validator_result.missing_components)
    assert _fields(missing) == validator_result.missing_components


def test_missing_information_agrees_with_validator_incomplete_peco():
    fw = ResearchFramework(type=FrameworkType.PECO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    missing = get_missing_information(project)
    validator_result = validate_framework(fw)
    assert len(missing) == len(validator_result.missing_components)
    assert _fields(missing) == validator_result.missing_components


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_result_is_deterministic_idea():
    project = _project(state=ResearchState.IDEA)
    r1 = get_missing_information(project)
    r2 = get_missing_information(project)
    assert _fields(r1) == _fields(r2)


def test_result_is_deterministic_question_defined():
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    r1 = get_missing_information(project)
    r2 = get_missing_information(project)
    assert _fields(r1) == _fields(r2)


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_project_state_not_mutated():
    project = _project(state=ResearchState.IDEA)
    get_missing_information(project)
    assert project.state == ResearchState.IDEA


def test_project_question_not_mutated():
    project = _project(state=ResearchState.IDEA)
    get_missing_information(project)
    assert project.research_question is None


def test_project_framework_not_mutated():
    fw = ResearchFramework(type=FrameworkType.PICO)
    project = _project(state=ResearchState.QUESTION_DEFINED, framework=fw)
    get_missing_information(project)
    assert project.framework.population is None
    assert project.framework.intervention is None


def test_project_tasks_not_mutated():
    project = _project(state=ResearchState.IDEA)
    original_count = len(project.tasks)
    get_missing_information(project)
    assert len(project.tasks) == original_count


# ---------------------------------------------------------------------------
# States beyond implemented rules return empty
# ---------------------------------------------------------------------------

def test_design_selected_returns_empty():
    project = _project(state=ResearchState.DESIGN_SELECTED)
    assert get_missing_information(project) == []


def test_protocol_ready_returns_empty():
    project = _project(state=ResearchState.PROTOCOL_READY)
    assert get_missing_information(project) == []


def test_literature_search_returns_empty():
    project = _project(state=ResearchState.LITERATURE_SEARCH)
    assert get_missing_information(project) == []


def test_ready_for_submission_returns_empty():
    project = _project(state=ResearchState.READY_FOR_SUBMISSION)
    assert get_missing_information(project) == []


# ---------------------------------------------------------------------------
# Public import
# ---------------------------------------------------------------------------

def test_get_missing_information_importable_from_services():
    from services import get_missing_information as fn
    assert callable(fn)


def test_missing_information_model_importable_from_services():
    from services import MissingInformation
    assert MissingInformation is not None
