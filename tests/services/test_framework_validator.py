"""Tests for the Framework Validation Engine."""
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
from services.framework_validator import (
    FrameworkValidationResult,
    FrameworkValidationStatus,
    validate_framework,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pico(**kwargs) -> ResearchFramework:
    defaults = dict(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    defaults.update(kwargs)
    return ResearchFramework(**defaults)


def _peco(**kwargs) -> ResearchFramework:
    defaults = dict(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        exposure=Exposure(description="Smoking"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer"),
    )
    defaults.update(kwargs)
    return ResearchFramework(**defaults)


# ---------------------------------------------------------------------------
# PICO — complete
# ---------------------------------------------------------------------------

def test_complete_pico_returns_complete():
    result = validate_framework(_pico())
    assert result.status == FrameworkValidationStatus.COMPLETE


def test_complete_pico_no_missing_components():
    result = validate_framework(_pico())
    assert result.missing_components == []


def test_complete_pico_framework_type_correct():
    result = validate_framework(_pico())
    assert result.framework_type == FrameworkType.PICO


# ---------------------------------------------------------------------------
# PICO — individual missing components
# ---------------------------------------------------------------------------

def test_pico_missing_population_is_incomplete():
    result = validate_framework(_pico(population=None))
    assert result.status == FrameworkValidationStatus.INCOMPLETE
    assert "Population" in result.missing_components


def test_pico_missing_intervention_is_incomplete():
    result = validate_framework(_pico(intervention=None))
    assert result.status == FrameworkValidationStatus.INCOMPLETE
    assert "Intervention" in result.missing_components


def test_pico_missing_comparator_is_incomplete():
    result = validate_framework(_pico(comparator=None))
    assert result.status == FrameworkValidationStatus.INCOMPLETE
    assert "Comparator" in result.missing_components


def test_pico_missing_outcome_is_incomplete():
    result = validate_framework(_pico(outcome=None))
    assert result.status == FrameworkValidationStatus.INCOMPLETE
    assert "Outcome" in result.missing_components


# ---------------------------------------------------------------------------
# PICO — multiple missing in canonical order
# ---------------------------------------------------------------------------

def test_pico_all_missing_returns_canonical_order():
    fw = ResearchFramework(type=FrameworkType.PICO)
    result = validate_framework(fw)
    assert result.missing_components == [
        "Population", "Intervention", "Comparator", "Outcome"
    ]


def test_pico_missing_population_and_outcome_canonical_order():
    result = validate_framework(_pico(population=None, outcome=None))
    assert result.missing_components == ["Population", "Outcome"]


def test_pico_missing_intervention_and_comparator_canonical_order():
    result = validate_framework(_pico(intervention=None, comparator=None))
    assert result.missing_components == ["Intervention", "Comparator"]


# ---------------------------------------------------------------------------
# PICO — exposure is never reported as missing
# ---------------------------------------------------------------------------

def test_pico_exposure_never_reported_missing_when_absent():
    result = validate_framework(_pico())
    assert "Exposure" not in result.missing_components


def test_pico_exposure_never_reported_missing_all_empty():
    fw = ResearchFramework(type=FrameworkType.PICO)
    result = validate_framework(fw)
    assert "Exposure" not in result.missing_components


# ---------------------------------------------------------------------------
# PECO — complete
# ---------------------------------------------------------------------------

def test_complete_peco_returns_complete():
    result = validate_framework(_peco())
    assert result.status == FrameworkValidationStatus.COMPLETE


def test_complete_peco_no_missing_components():
    result = validate_framework(_peco())
    assert result.missing_components == []


def test_complete_peco_framework_type_correct():
    result = validate_framework(_peco())
    assert result.framework_type == FrameworkType.PECO


# ---------------------------------------------------------------------------
# PECO — individual missing components
# ---------------------------------------------------------------------------

def test_peco_missing_population_is_incomplete():
    result = validate_framework(_peco(population=None))
    assert result.status == FrameworkValidationStatus.INCOMPLETE
    assert "Population" in result.missing_components


def test_peco_missing_exposure_is_incomplete():
    result = validate_framework(_peco(exposure=None))
    assert result.status == FrameworkValidationStatus.INCOMPLETE
    assert "Exposure" in result.missing_components


def test_peco_missing_comparator_is_incomplete():
    result = validate_framework(_peco(comparator=None))
    assert result.status == FrameworkValidationStatus.INCOMPLETE
    assert "Comparator" in result.missing_components


def test_peco_missing_outcome_is_incomplete():
    result = validate_framework(_peco(outcome=None))
    assert result.status == FrameworkValidationStatus.INCOMPLETE
    assert "Outcome" in result.missing_components


# ---------------------------------------------------------------------------
# PECO — multiple missing in canonical order
# ---------------------------------------------------------------------------

def test_peco_all_missing_returns_canonical_order():
    fw = ResearchFramework(type=FrameworkType.PECO)
    result = validate_framework(fw)
    assert result.missing_components == [
        "Population", "Exposure", "Comparator", "Outcome"
    ]


def test_peco_missing_population_and_outcome_canonical_order():
    result = validate_framework(_peco(population=None, outcome=None))
    assert result.missing_components == ["Population", "Outcome"]


def test_peco_missing_exposure_and_comparator_canonical_order():
    result = validate_framework(_peco(exposure=None, comparator=None))
    assert result.missing_components == ["Exposure", "Comparator"]


# ---------------------------------------------------------------------------
# PECO — intervention is never reported as missing
# ---------------------------------------------------------------------------

def test_peco_intervention_never_reported_missing_when_absent():
    result = validate_framework(_peco())
    assert "Intervention" not in result.missing_components


def test_peco_intervention_never_reported_missing_all_empty():
    fw = ResearchFramework(type=FrameworkType.PECO)
    result = validate_framework(fw)
    assert "Intervention" not in result.missing_components


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_validation_is_deterministic_complete():
    fw = _pico()
    r1 = validate_framework(fw)
    r2 = validate_framework(fw)
    assert r1.status == r2.status
    assert r1.missing_components == r2.missing_components


def test_validation_is_deterministic_incomplete():
    fw = ResearchFramework(type=FrameworkType.PICO)
    r1 = validate_framework(fw)
    r2 = validate_framework(fw)
    assert r1.status == r2.status
    assert r1.missing_components == r2.missing_components


def test_validation_does_not_mutate_framework():
    fw = _pico(intervention=None)
    before_intervention = fw.intervention
    validate_framework(fw)
    assert fw.intervention == before_intervention


def test_validation_does_not_mutate_peco_framework():
    fw = _peco(exposure=None)
    before_exposure = fw.exposure
    validate_framework(fw)
    assert fw.exposure == before_exposure


# ---------------------------------------------------------------------------
# Compatibility — framework.is_complete agrees with validator
# ---------------------------------------------------------------------------

def test_is_complete_agrees_with_validator_complete_pico():
    fw = _pico()
    result = validate_framework(fw)
    assert fw.is_complete is (result.status == FrameworkValidationStatus.COMPLETE)


def test_is_complete_agrees_with_validator_incomplete_pico():
    fw = _pico(intervention=None)
    result = validate_framework(fw)
    assert fw.is_complete is (result.status == FrameworkValidationStatus.COMPLETE)


def test_is_complete_agrees_with_validator_complete_peco():
    fw = _peco()
    result = validate_framework(fw)
    assert fw.is_complete is (result.status == FrameworkValidationStatus.COMPLETE)


def test_is_complete_agrees_with_validator_incomplete_peco():
    fw = _peco(exposure=None)
    result = validate_framework(fw)
    assert fw.is_complete is (result.status == FrameworkValidationStatus.COMPLETE)


def test_is_complete_agrees_with_validator_all_missing_pico():
    fw = ResearchFramework(type=FrameworkType.PICO)
    result = validate_framework(fw)
    assert fw.is_complete is False
    assert result.status == FrameworkValidationStatus.INCOMPLETE


def test_is_complete_agrees_with_validator_all_missing_peco():
    fw = ResearchFramework(type=FrameworkType.PECO)
    result = validate_framework(fw)
    assert fw.is_complete is False
    assert result.status == FrameworkValidationStatus.INCOMPLETE


# ---------------------------------------------------------------------------
# Result is a proper model
# ---------------------------------------------------------------------------

def test_validation_result_is_pydantic_model():
    result = validate_framework(_pico())
    assert isinstance(result, FrameworkValidationResult)


def test_validation_result_missing_components_is_list():
    result = validate_framework(_pico())
    assert isinstance(result.missing_components, list)
