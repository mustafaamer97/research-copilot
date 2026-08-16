"""Tests for framework components and ResearchFramework."""
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


# --- Component tests ---

def test_population_accepted():
    p = Population(description="Adults over 65")
    assert p.description == "Adults over 65"


def test_intervention_accepted():
    i = Intervention(description="Aspirin 100mg daily")
    assert i.description == "Aspirin 100mg daily"


def test_exposure_accepted():
    e = Exposure(description="Cigarette smoking")
    assert e.description == "Cigarette smoking"


def test_comparator_accepted():
    c = Comparator(description="Placebo")
    assert c.description == "Placebo"


def test_outcome_accepted():
    o = Outcome(description="All-cause mortality")
    assert o.description == "All-cause mortality"


# --- PICO tests ---

def test_pico_complete():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    assert fw.is_complete is True


def test_pico_incomplete_missing_intervention():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    assert fw.is_complete is False


def test_pico_can_exist_with_no_components():
    fw = ResearchFramework(type=FrameworkType.PICO)
    assert fw.is_complete is False


def test_pico_does_not_require_exposure():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    assert fw.exposure is None
    assert fw.is_complete is True


def test_pico_missing_values_not_invented():
    fw = ResearchFramework(type=FrameworkType.PICO)
    assert fw.population is None
    assert fw.intervention is None
    assert fw.comparator is None
    assert fw.outcome is None


# --- PECO tests ---

def test_peco_complete():
    fw = ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        exposure=Exposure(description="Smoking"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer"),
    )
    assert fw.is_complete is True


def test_peco_incomplete_missing_exposure():
    fw = ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer"),
    )
    assert fw.is_complete is False


def test_peco_can_exist_with_no_components():
    fw = ResearchFramework(type=FrameworkType.PECO)
    assert fw.is_complete is False


def test_peco_does_not_require_intervention():
    fw = ResearchFramework(
        type=FrameworkType.PECO,
        population=Population(description="Adults"),
        exposure=Exposure(description="Smoking"),
        comparator=Comparator(description="Non-smokers"),
        outcome=Outcome(description="Lung cancer"),
    )
    assert fw.intervention is None
    assert fw.is_complete is True


def test_peco_missing_values_not_invented():
    fw = ResearchFramework(type=FrameworkType.PECO)
    assert fw.exposure is None
    assert fw.comparator is None
    assert fw.outcome is None


# --- Completeness is deterministic ---

def test_pico_completeness_is_deterministic():
    fw = ResearchFramework(
        type=FrameworkType.PICO,
        population=Population(description="Adults"),
        intervention=Intervention(description="Drug A"),
        comparator=Comparator(description="Placebo"),
        outcome=Outcome(description="Mortality"),
    )
    assert fw.is_complete is fw.is_complete


def test_peco_completeness_is_deterministic():
    fw = ResearchFramework(type=FrameworkType.PECO)
    assert fw.is_complete is fw.is_complete
