"""Tests for the deterministic search strategy builder."""
import pytest

from domain.framework import FrameworkType
from domain.literature_search import LiteratureSearchStrategy
from services.search_strategy_builder import (
    SearchStrategyValidationError,
    build_search_strategy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pico(**kwargs):
    defaults = dict(
        framework_type=FrameworkType.PICO,
        population_terms=["Adults with type 2 diabetes"],
        intervention_terms=["Metformin"],
        comparator_terms=["Placebo"],
        outcome_terms=["Cardiovascular mortality"],
    )
    defaults.update(kwargs)
    return build_search_strategy(**defaults)


def _peco(**kwargs):
    defaults = dict(
        framework_type=FrameworkType.PECO,
        population_terms=["Adults"],
        exposure_terms=["Cigarette smoking"],
        comparator_terms=["Non-smokers"],
        outcome_terms=["Lung cancer incidence"],
    )
    defaults.update(kwargs)
    return build_search_strategy(**defaults)


# ---------------------------------------------------------------------------
# 1. Complete PICO creates a valid strategy
# ---------------------------------------------------------------------------

def test_complete_pico_creates_strategy():
    strategy = _pico()
    assert isinstance(strategy, LiteratureSearchStrategy)
    assert strategy.framework_type == FrameworkType.PICO


def test_pico_strategy_has_boolean_query():
    strategy = _pico()
    assert strategy.boolean_query is not None
    assert len(strategy.boolean_query) > 0


# ---------------------------------------------------------------------------
# 2. Population terms preserved
# ---------------------------------------------------------------------------

def test_pico_population_terms_preserved():
    terms = ["Adults with type 2 diabetes", "T2DM"]
    strategy = _pico(population_terms=terms)
    assert strategy.population_terms == terms


# ---------------------------------------------------------------------------
# 3. Intervention terms preserved
# ---------------------------------------------------------------------------

def test_pico_intervention_terms_preserved():
    terms = ["Metformin", "metformin hydrochloride"]
    strategy = _pico(intervention_terms=terms)
    assert strategy.intervention_terms == terms


# ---------------------------------------------------------------------------
# 4. Comparator terms preserved
# ---------------------------------------------------------------------------

def test_pico_comparator_terms_preserved():
    terms = ["Placebo", "standard care"]
    strategy = _pico(comparator_terms=terms)
    assert strategy.comparator_terms == terms


# ---------------------------------------------------------------------------
# 5. Outcome terms preserved
# ---------------------------------------------------------------------------

def test_pico_outcome_terms_preserved():
    terms = ["Cardiovascular mortality", "all-cause mortality"]
    strategy = _pico(outcome_terms=terms)
    assert strategy.outcome_terms == terms


# ---------------------------------------------------------------------------
# 6. Boolean query is deterministic
# ---------------------------------------------------------------------------

def test_pico_boolean_query_contains_all_terms():
    strategy = _pico(
        population_terms=["Adults"],
        intervention_terms=["Drug A"],
        comparator_terms=["Placebo"],
        outcome_terms=["Mortality"],
    )
    query = strategy.boolean_query
    assert "Adults" in query
    assert "Drug A" in query
    assert "Placebo" in query
    assert "Mortality" in query


def test_pico_boolean_query_uses_and_between_components():
    strategy = _pico(
        population_terms=["Adults"],
        intervention_terms=["Drug A"],
        comparator_terms=["Placebo"],
        outcome_terms=["Mortality"],
    )
    assert " AND " in strategy.boolean_query


def test_pico_multiple_terms_in_component_use_or():
    strategy = _pico(population_terms=["Adults", "Elderly"])
    assert " OR " in strategy.boolean_query
    assert "Adults" in strategy.boolean_query
    assert "Elderly" in strategy.boolean_query


# ---------------------------------------------------------------------------
# 7. Same inputs produce identical strategy
# ---------------------------------------------------------------------------

def test_pico_deterministic_same_inputs():
    s1 = _pico()
    s2 = _pico()
    assert s1.boolean_query == s2.boolean_query
    assert s1.population_terms == s2.population_terms
    assert s1.intervention_terms == s2.intervention_terms


# ---------------------------------------------------------------------------
# 8. Complete PECO creates a valid strategy
# ---------------------------------------------------------------------------

def test_complete_peco_creates_strategy():
    strategy = _peco()
    assert isinstance(strategy, LiteratureSearchStrategy)
    assert strategy.framework_type == FrameworkType.PECO


def test_peco_boolean_query_contains_exposure_terms():
    strategy = _peco(exposure_terms=["Cigarette smoking", "tobacco use"])
    assert "Cigarette smoking" in strategy.boolean_query
    assert "tobacco use" in strategy.boolean_query


# ---------------------------------------------------------------------------
# 9. Exposure terms preserved
# ---------------------------------------------------------------------------

def test_peco_exposure_terms_preserved():
    terms = ["Cigarette smoking", "tobacco use"]
    strategy = _peco(exposure_terms=terms)
    assert strategy.exposure_terms == terms


# ---------------------------------------------------------------------------
# 10. Intervention rejected for PECO when exposure is required
# ---------------------------------------------------------------------------

def test_peco_missing_exposure_raises():
    with pytest.raises(SearchStrategyValidationError) as exc_info:
        build_search_strategy(
            framework_type=FrameworkType.PECO,
            population_terms=["Adults"],
            intervention_terms=["Drug A"],  # wrong field for PECO
            comparator_terms=["Non-smokers"],
            outcome_terms=["Lung cancer"],
        )
    assert "exposure_terms" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 11. Missing population rejected
# ---------------------------------------------------------------------------

def test_pico_missing_population_rejected():
    with pytest.raises(SearchStrategyValidationError) as exc_info:
        build_search_strategy(
            framework_type=FrameworkType.PICO,
            population_terms=[],
            intervention_terms=["Drug A"],
            comparator_terms=["Placebo"],
            outcome_terms=["Mortality"],
        )
    assert "population_terms" in str(exc_info.value)


def test_peco_missing_population_rejected():
    with pytest.raises(SearchStrategyValidationError) as exc_info:
        build_search_strategy(
            framework_type=FrameworkType.PECO,
            population_terms=[],
            exposure_terms=["Smoking"],
            comparator_terms=["Non-smokers"],
            outcome_terms=["Lung cancer"],
        )
    assert "population_terms" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 12. Missing intervention rejected for PICO
# ---------------------------------------------------------------------------

def test_pico_missing_intervention_rejected():
    with pytest.raises(SearchStrategyValidationError) as exc_info:
        build_search_strategy(
            framework_type=FrameworkType.PICO,
            population_terms=["Adults"],
            intervention_terms=[],
            comparator_terms=["Placebo"],
            outcome_terms=["Mortality"],
        )
    assert "intervention_terms" in str(exc_info.value)


def test_pico_none_intervention_rejected():
    with pytest.raises(SearchStrategyValidationError):
        build_search_strategy(
            framework_type=FrameworkType.PICO,
            population_terms=["Adults"],
            comparator_terms=["Placebo"],
            outcome_terms=["Mortality"],
        )


# ---------------------------------------------------------------------------
# 13. Missing exposure rejected for PECO
# ---------------------------------------------------------------------------

def test_peco_missing_exposure_terms_rejected():
    with pytest.raises(SearchStrategyValidationError) as exc_info:
        build_search_strategy(
            framework_type=FrameworkType.PECO,
            population_terms=["Adults"],
            exposure_terms=[],
            comparator_terms=["Non-smokers"],
            outcome_terms=["Lung cancer"],
        )
    assert "exposure_terms" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 14. Missing comparator rejected
# ---------------------------------------------------------------------------

def test_pico_missing_comparator_rejected():
    with pytest.raises(SearchStrategyValidationError) as exc_info:
        build_search_strategy(
            framework_type=FrameworkType.PICO,
            population_terms=["Adults"],
            intervention_terms=["Drug A"],
            comparator_terms=[],
            outcome_terms=["Mortality"],
        )
    assert "comparator_terms" in str(exc_info.value)


def test_peco_missing_comparator_rejected():
    with pytest.raises(SearchStrategyValidationError) as exc_info:
        build_search_strategy(
            framework_type=FrameworkType.PECO,
            population_terms=["Adults"],
            exposure_terms=["Smoking"],
            comparator_terms=[],
            outcome_terms=["Lung cancer"],
        )
    assert "comparator_terms" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 15. Missing outcome rejected
# ---------------------------------------------------------------------------

def test_pico_missing_outcome_rejected():
    with pytest.raises(SearchStrategyValidationError) as exc_info:
        build_search_strategy(
            framework_type=FrameworkType.PICO,
            population_terms=["Adults"],
            intervention_terms=["Drug A"],
            comparator_terms=["Placebo"],
            outcome_terms=[],
        )
    assert "outcome_terms" in str(exc_info.value)


def test_peco_missing_outcome_rejected():
    with pytest.raises(SearchStrategyValidationError) as exc_info:
        build_search_strategy(
            framework_type=FrameworkType.PECO,
            population_terms=["Adults"],
            exposure_terms=["Smoking"],
            comparator_terms=["Non-smokers"],
            outcome_terms=[],
        )
    assert "outcome_terms" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 16. No synonyms generated
# ---------------------------------------------------------------------------

def test_no_synonyms_added_to_intervention():
    strategy = _pico(intervention_terms=["Metformin"])
    assert strategy.intervention_terms == ["Metformin"]
    assert len(strategy.intervention_terms) == 1


def test_no_synonyms_added_to_population():
    strategy = _pico(population_terms=["Adults"])
    assert strategy.population_terms == ["Adults"]
    assert len(strategy.population_terms) == 1


# ---------------------------------------------------------------------------
# 17. No MeSH terms generated
# ---------------------------------------------------------------------------

def test_no_mesh_in_terms():
    strategy = _pico(intervention_terms=["Aspirin"])
    combined = " ".join(strategy.intervention_terms)
    assert "[MeSH]" not in combined
    assert "[mh]" not in combined.lower()


def test_no_mesh_in_boolean_query():
    strategy = _pico(intervention_terms=["Aspirin"])
    assert "[MeSH]" not in strategy.boolean_query
    assert "[mh]" not in strategy.boolean_query.lower()


# ---------------------------------------------------------------------------
# 18. No extra terms added
# ---------------------------------------------------------------------------

def test_no_extra_terms_added_to_population():
    terms = ["Elderly patients"]
    strategy = _pico(population_terms=terms)
    assert strategy.population_terms == terms


def test_no_extra_terms_added_to_outcome():
    terms = ["All-cause mortality"]
    strategy = _pico(outcome_terms=terms)
    assert strategy.outcome_terms == terms


# ---------------------------------------------------------------------------
# 19. Duplicate supplied terms are preserved
# ---------------------------------------------------------------------------

def test_duplicate_terms_preserved_in_intervention():
    terms = ["Metformin", "Metformin"]
    strategy = _pico(intervention_terms=terms)
    assert strategy.intervention_terms == ["Metformin", "Metformin"]


def test_duplicate_terms_appear_in_query():
    terms = ["Metformin", "Metformin"]
    strategy = _pico(intervention_terms=terms)
    assert strategy.boolean_query.count("Metformin") == 2


# ---------------------------------------------------------------------------
# 20. Boolean-looking text treated as term, not executable syntax
# ---------------------------------------------------------------------------

def test_and_in_term_preserved_literally():
    strategy = _pico(population_terms=["Adults AND Elderly"])
    assert strategy.population_terms == ["Adults AND Elderly"]


def test_or_in_term_preserved_literally():
    strategy = _pico(population_terms=["Men OR Women"])
    assert strategy.population_terms == ["Men OR Women"]


def test_and_term_quoted_in_query():
    strategy = _pico(population_terms=["Adults AND Elderly"])
    assert '"Adults AND Elderly"' in strategy.boolean_query


def test_or_term_quoted_in_query():
    strategy = _pico(population_terms=["Men OR Women"])
    assert '"Men OR Women"' in strategy.boolean_query


# ---------------------------------------------------------------------------
# 21. Quotation marks handled deterministically
# ---------------------------------------------------------------------------

def test_embedded_quote_in_term_is_escaped():
    strategy = _pico(population_terms=['Adults with "diabetes"'])
    assert strategy.population_terms == ['Adults with "diabetes"']
    assert '\\"' in strategy.boolean_query


def test_term_with_quotes_does_not_break_query():
    strategy = _pico(population_terms=['He said "hello"'])
    query = strategy.boolean_query
    assert query is not None
    assert "hello" in query


# ---------------------------------------------------------------------------
# 22. Parentheses in terms do not alter grouping
# ---------------------------------------------------------------------------

def test_parentheses_in_term_preserved():
    term = "Adults (18-80 years)"
    strategy = _pico(population_terms=[term])
    assert strategy.population_terms == [term]


def test_parentheses_term_quoted_in_query():
    term = "Adults (18-80 years)"
    strategy = _pico(population_terms=[term])
    assert f'"{term}"' in strategy.boolean_query


# ---------------------------------------------------------------------------
# 23. No external API called
# ---------------------------------------------------------------------------

def test_no_http_on_build(monkeypatch):
    import urllib.request
    called = []
    original = urllib.request.urlopen

    def mock_urlopen(*args, **kwargs):
        called.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    _pico()
    assert called == []


# ---------------------------------------------------------------------------
# 24. No AI called
# ---------------------------------------------------------------------------

def test_build_has_no_ai_methods():
    from services import build_search_strategy as fn
    assert callable(fn)
    # Structural: no openai/anthropic/google imports in the module
    import services.search_strategy_builder as mod
    import inspect
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


# ---------------------------------------------------------------------------
# 25. No HTTP performed
# ---------------------------------------------------------------------------

def test_build_has_no_http_imports():
    import services.search_strategy_builder as mod
    import inspect
    source = inspect.getsource(mod)
    assert "requests" not in source
    assert "httpx" not in source
    assert "urllib.request.urlopen" not in source


# ---------------------------------------------------------------------------
# Public import
# ---------------------------------------------------------------------------

def test_build_search_strategy_importable_from_services():
    from services import build_search_strategy as fn
    assert callable(fn)


def test_search_strategy_validation_error_importable_from_services():
    from services import SearchStrategyValidationError
    assert issubclass(SearchStrategyValidationError, Exception)


# ---------------------------------------------------------------------------
# Result immutability
# ---------------------------------------------------------------------------

def test_returned_strategy_is_immutable():
    strategy = _pico()
    with pytest.raises(Exception):
        strategy.population_terms = ["mutated"]


def test_returned_strategy_boolean_query_immutable():
    strategy = _pico()
    with pytest.raises(Exception):
        strategy.boolean_query = "mutated"


# ---------------------------------------------------------------------------
# PECO — intervention terms stored as empty (not converted to exposure)
# ---------------------------------------------------------------------------

def test_peco_intervention_terms_empty_in_result():
    strategy = _peco()
    assert strategy.intervention_terms == []


def test_pico_exposure_terms_empty_in_result():
    strategy = _pico()
    assert strategy.exposure_terms == []
