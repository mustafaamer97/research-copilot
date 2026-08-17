"""Tests for the Screening Criteria domain contract."""
import pytest

from screening.criteria import ExclusionCriteria, InclusionCriteria, ScreeningCriteria


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_inclusion(**kwargs) -> InclusionCriteria:
    defaults = dict(
        description=(
            "RCTs or cohort studies in adults aged 18+ with type 2 diabetes "
            "receiving pharmacological intervention."
        )
    )
    defaults.update(kwargs)
    return InclusionCriteria(**defaults)


def _valid_exclusion(**kwargs) -> ExclusionCriteria:
    defaults = dict(
        description=(
            "Case reports, editorials, conference abstracts, animal studies, "
            "and studies with fewer than 100 participants."
        )
    )
    defaults.update(kwargs)
    return ExclusionCriteria(**defaults)


def _valid_criteria(**kwargs) -> ScreeningCriteria:
    defaults = dict(
        inclusion_criteria=_valid_inclusion(),
        exclusion_criteria=_valid_exclusion(),
    )
    defaults.update(kwargs)
    return ScreeningCriteria(**defaults)


# ---------------------------------------------------------------------------
# InclusionCriteria
# ---------------------------------------------------------------------------

def test_valid_inclusion_criteria_accepted():
    ic = _valid_inclusion()
    assert ic is not None
    assert ic.description


def test_inclusion_criteria_description_preserved():
    desc = "Studies reporting HbA1c outcomes in adults with T2DM."
    ic = InclusionCriteria(description=desc)
    assert ic.description == desc


def test_empty_inclusion_criteria_rejected():
    with pytest.raises(Exception):
        InclusionCriteria(description="")


def test_whitespace_inclusion_criteria_rejected():
    with pytest.raises(Exception):
        InclusionCriteria(description="   ")


def test_inclusion_criteria_is_immutable():
    ic = _valid_inclusion()
    with pytest.raises(Exception):
        ic.description = "Mutated"


# ---------------------------------------------------------------------------
# ExclusionCriteria
# ---------------------------------------------------------------------------

def test_valid_exclusion_criteria_accepted():
    ec = _valid_exclusion()
    assert ec is not None
    assert ec.description


def test_exclusion_criteria_description_preserved():
    desc = "Animal studies and in-vitro experiments."
    ec = ExclusionCriteria(description=desc)
    assert ec.description == desc


def test_empty_exclusion_criteria_rejected():
    with pytest.raises(Exception):
        ExclusionCriteria(description="")


def test_whitespace_exclusion_criteria_rejected():
    with pytest.raises(Exception):
        ExclusionCriteria(description="   ")


def test_exclusion_criteria_is_immutable():
    ec = _valid_exclusion()
    with pytest.raises(Exception):
        ec.description = "Mutated"


# ---------------------------------------------------------------------------
# TEST 8: Valid ScreeningCriteria
# ---------------------------------------------------------------------------

def test_valid_screening_criteria_accepted():
    sc = _valid_criteria()
    assert sc is not None


def test_screening_criteria_has_inclusion():
    sc = _valid_criteria()
    assert sc.inclusion_criteria is not None


def test_screening_criteria_has_exclusion():
    sc = _valid_criteria()
    assert sc.exclusion_criteria is not None


def test_screening_criteria_inclusion_type():
    sc = _valid_criteria()
    assert isinstance(sc.inclusion_criteria, InclusionCriteria)


def test_screening_criteria_exclusion_type():
    sc = _valid_criteria()
    assert isinstance(sc.exclusion_criteria, ExclusionCriteria)


# ---------------------------------------------------------------------------
# TEST 9: Missing inclusion criteria
# ---------------------------------------------------------------------------

def test_missing_inclusion_criteria_rejected():
    with pytest.raises(Exception):
        ScreeningCriteria(
            exclusion_criteria=_valid_exclusion(),
        )


def test_none_inclusion_criteria_rejected():
    with pytest.raises(Exception):
        ScreeningCriteria(
            inclusion_criteria=None,
            exclusion_criteria=_valid_exclusion(),
        )


# ---------------------------------------------------------------------------
# TEST 10: Missing exclusion criteria
# ---------------------------------------------------------------------------

def test_missing_exclusion_criteria_rejected():
    with pytest.raises(Exception):
        ScreeningCriteria(
            inclusion_criteria=_valid_inclusion(),
        )


def test_none_exclusion_criteria_rejected():
    with pytest.raises(Exception):
        ScreeningCriteria(
            inclusion_criteria=_valid_inclusion(),
            exclusion_criteria=None,
        )


# ---------------------------------------------------------------------------
# TEST 11: No invention
# ---------------------------------------------------------------------------

def test_screening_criteria_has_no_auto_generated_content():
    sc = _valid_criteria()
    # Only inclusion and exclusion fields — no extra invented fields
    fields = set(sc.model_fields.keys())
    assert fields == {"inclusion_criteria", "exclusion_criteria"}


def test_inclusion_description_not_modified():
    desc = "Randomised controlled trials only."
    sc = ScreeningCriteria(
        inclusion_criteria=InclusionCriteria(description=desc),
        exclusion_criteria=_valid_exclusion(),
    )
    assert sc.inclusion_criteria.description == desc


def test_exclusion_description_not_modified():
    desc = "Non-English publications."
    sc = ScreeningCriteria(
        inclusion_criteria=_valid_inclusion(),
        exclusion_criteria=ExclusionCriteria(description=desc),
    )
    assert sc.exclusion_criteria.description == desc


def test_no_population_invented():
    sc = _valid_criteria()
    assert not hasattr(sc, "population")


def test_no_intervention_invented():
    sc = _valid_criteria()
    assert not hasattr(sc, "intervention")


def test_no_study_design_invented():
    sc = _valid_criteria()
    assert not hasattr(sc, "study_design")


# ---------------------------------------------------------------------------
# TEST 12: Preservation
# ---------------------------------------------------------------------------

def test_inclusion_description_preserved_exactly():
    desc = (
        "Prospective cohort studies with ≥ 1 year follow-up in adults "
        "with confirmed type 2 diabetes."
    )
    sc = ScreeningCriteria(
        inclusion_criteria=InclusionCriteria(description=desc),
        exclusion_criteria=_valid_exclusion(),
    )
    assert sc.inclusion_criteria.description == desc


def test_exclusion_description_preserved_exactly():
    desc = "Cross-sectional studies; studies without a control group; grey literature."
    sc = ScreeningCriteria(
        inclusion_criteria=_valid_inclusion(),
        exclusion_criteria=ExclusionCriteria(description=desc),
    )
    assert sc.exclusion_criteria.description == desc


# ---------------------------------------------------------------------------
# TEST 13: No AI
# ---------------------------------------------------------------------------

def test_no_ai_imports_in_criteria_module():
    import inspect
    import screening.criteria as mod
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


def test_no_http_in_criteria_module():
    import inspect
    import screening.criteria as mod
    source = inspect.getsource(mod)
    assert "urllib.request.urlopen" not in source
    assert "requests" not in source


def test_criteria_construction_requires_no_external_service():
    sc = _valid_criteria()
    assert sc is not None


# ---------------------------------------------------------------------------
# Immutability of ScreeningCriteria
# ---------------------------------------------------------------------------

def test_screening_criteria_is_immutable():
    sc = _valid_criteria()
    with pytest.raises(Exception):
        sc.inclusion_criteria = _valid_inclusion()


def test_screening_criteria_exclusion_immutable():
    sc = _valid_criteria()
    with pytest.raises(Exception):
        sc.exclusion_criteria = _valid_exclusion()


# ---------------------------------------------------------------------------
# No parallel concepts
# ---------------------------------------------------------------------------

def test_no_parallel_inclusion_type():
    import screening.criteria as mod
    for forbidden in ("ScreeningInclusionCriteria", "ScreeningCriteriaModel"):
        assert not hasattr(mod, forbidden)


def test_no_parallel_exclusion_type():
    import screening.criteria as mod
    assert not hasattr(mod, "ScreeningExclusionCriteria")


# ---------------------------------------------------------------------------
# Public imports
# ---------------------------------------------------------------------------

def test_screening_criteria_importable_from_screening():
    from screening import ScreeningCriteria
    assert ScreeningCriteria is not None


def test_inclusion_criteria_importable_from_screening():
    from screening import InclusionCriteria
    assert InclusionCriteria is not None


def test_exclusion_criteria_importable_from_screening():
    from screening import ExclusionCriteria
    assert ExclusionCriteria is not None


def test_all_screening_exports_present():
    import screening
    for name in ("ScreeningCriteria", "InclusionCriteria", "ExclusionCriteria"):
        assert name in screening.__all__
