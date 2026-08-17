"""Tests for LiteratureSearchStrategy domain contract."""
import pytest

from domain.framework import FrameworkType
from domain.literature_search import LiteratureSearchStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pico_strategy(**kwargs) -> LiteratureSearchStrategy:
    defaults = dict(
        framework_type=FrameworkType.PICO,
        population_terms=["Adults with type 2 diabetes"],
        intervention_terms=["Metformin"],
        comparator_terms=["Placebo"],
        outcome_terms=["cardiovascular mortality"],
    )
    defaults.update(kwargs)
    return LiteratureSearchStrategy(**defaults)


def _peco_strategy(**kwargs) -> LiteratureSearchStrategy:
    defaults = dict(
        framework_type=FrameworkType.PECO,
        population_terms=["Adults"],
        exposure_terms=["Cigarette smoking"],
        comparator_terms=["Non-smokers"],
        outcome_terms=["Lung cancer incidence"],
    )
    defaults.update(kwargs)
    return LiteratureSearchStrategy(**defaults)


# ---------------------------------------------------------------------------
# 1. Valid PICO strategy can be created
# ---------------------------------------------------------------------------

def test_valid_pico_strategy_created():
    strategy = _pico_strategy()
    assert strategy is not None
    assert strategy.framework_type == FrameworkType.PICO


def test_pico_strategy_has_correct_framework_type():
    strategy = _pico_strategy()
    assert strategy.framework_type == FrameworkType.PICO


# ---------------------------------------------------------------------------
# 2. Valid PECO strategy can be created
# ---------------------------------------------------------------------------

def test_valid_peco_strategy_created():
    strategy = _peco_strategy()
    assert strategy is not None
    assert strategy.framework_type == FrameworkType.PECO


def test_peco_strategy_has_correct_framework_type():
    strategy = _peco_strategy()
    assert strategy.framework_type == FrameworkType.PECO


# ---------------------------------------------------------------------------
# 3. Terms are preserved exactly
# ---------------------------------------------------------------------------

def test_population_terms_preserved_exactly():
    terms = ["Adults with type 2 diabetes", "Age 18-80"]
    strategy = _pico_strategy(population_terms=terms)
    assert strategy.population_terms == terms


def test_intervention_terms_preserved_exactly():
    terms = ["Metformin", "metformin hydrochloride"]
    strategy = _pico_strategy(intervention_terms=terms)
    assert strategy.intervention_terms == terms


def test_comparator_terms_preserved_exactly():
    terms = ["Placebo", "standard care"]
    strategy = _pico_strategy(comparator_terms=terms)
    assert strategy.comparator_terms == terms


def test_outcome_terms_preserved_exactly():
    terms = ["cardiovascular mortality", "all-cause mortality"]
    strategy = _pico_strategy(outcome_terms=terms)
    assert strategy.outcome_terms == terms


def test_exposure_terms_preserved_exactly():
    terms = ["Cigarette smoking", "tobacco use"]
    strategy = _peco_strategy(exposure_terms=terms)
    assert strategy.exposure_terms == terms


def test_terms_not_normalized_or_expanded():
    strategy = _pico_strategy(intervention_terms=["Metformin"])
    assert strategy.intervention_terms == ["Metformin"]
    assert "metformin hydrochloride" not in strategy.intervention_terms
    assert "Glucophage" not in strategy.intervention_terms
    assert "biguanide" not in strategy.intervention_terms


# ---------------------------------------------------------------------------
# 4. Empty term collections are allowed
# ---------------------------------------------------------------------------

def test_empty_population_terms_allowed():
    strategy = _pico_strategy(population_terms=[])
    assert strategy.population_terms == []


def test_empty_intervention_terms_allowed():
    strategy = _pico_strategy(intervention_terms=[])
    assert strategy.intervention_terms == []


def test_empty_exposure_terms_allowed():
    strategy = _peco_strategy(exposure_terms=[])
    assert strategy.exposure_terms == []


def test_empty_comparator_terms_allowed():
    strategy = _pico_strategy(comparator_terms=[])
    assert strategy.comparator_terms == []


def test_empty_outcome_terms_allowed():
    strategy = _pico_strategy(outcome_terms=[])
    assert strategy.outcome_terms == []


def test_all_terms_empty_is_allowed():
    strategy = LiteratureSearchStrategy(framework_type=FrameworkType.PICO)
    assert strategy.population_terms == []
    assert strategy.intervention_terms == []
    assert strategy.exposure_terms == []
    assert strategy.comparator_terms == []
    assert strategy.outcome_terms == []


# ---------------------------------------------------------------------------
# 5. Boolean query can be omitted
# ---------------------------------------------------------------------------

def test_boolean_query_defaults_to_none():
    strategy = _pico_strategy()
    assert strategy.boolean_query is None


def test_boolean_query_omitted_is_valid():
    strategy = LiteratureSearchStrategy(framework_type=FrameworkType.PICO)
    assert strategy.boolean_query is None


# ---------------------------------------------------------------------------
# 6. Boolean query preserved exactly when supplied
# ---------------------------------------------------------------------------

def test_boolean_query_preserved_exactly():
    query = '("type 2 diabetes") AND ("Metformin") AND ("cardiovascular mortality")'
    strategy = _pico_strategy(boolean_query=query)
    assert strategy.boolean_query == query


def test_boolean_query_not_modified():
    query = "Adults AND Metformin NOT Placebo"
    strategy = _pico_strategy(boolean_query=query)
    assert strategy.boolean_query == query


# ---------------------------------------------------------------------------
# 7. Missing framework type is rejected
# ---------------------------------------------------------------------------

def test_missing_framework_type_is_rejected():
    with pytest.raises(Exception):
        LiteratureSearchStrategy()


# ---------------------------------------------------------------------------
# 8. Unsupported framework type is rejected
# ---------------------------------------------------------------------------

def test_unsupported_framework_type_string_is_rejected():
    with pytest.raises(Exception):
        LiteratureSearchStrategy(framework_type="PRISMA")


def test_unsupported_framework_type_integer_is_rejected():
    with pytest.raises(Exception):
        LiteratureSearchStrategy(framework_type=99)


# ---------------------------------------------------------------------------
# 9. Source-specific fields are not required
# ---------------------------------------------------------------------------

def test_strategy_has_no_pubmed_specific_field():
    strategy = _pico_strategy()
    assert not hasattr(strategy, "pubmed_query")
    assert not hasattr(strategy, "mesh_terms")


def test_strategy_has_no_europe_pmc_specific_field():
    strategy = _pico_strategy()
    assert not hasattr(strategy, "europe_pmc_query")


def test_strategy_has_no_openalex_specific_field():
    strategy = _pico_strategy()
    assert not hasattr(strategy, "openalex_filter")


def test_strategy_has_no_crossref_specific_field():
    strategy = _pico_strategy()
    assert not hasattr(strategy, "crossref_query")


# ---------------------------------------------------------------------------
# 10. No synonym generation
# ---------------------------------------------------------------------------

def test_no_synonyms_generated_for_population():
    strategy = _pico_strategy(population_terms=["Adults"])
    assert strategy.population_terms == ["Adults"]
    assert len(strategy.population_terms) == 1


def test_no_synonyms_generated_for_intervention():
    strategy = _pico_strategy(intervention_terms=["Aspirin"])
    assert strategy.intervention_terms == ["Aspirin"]
    assert len(strategy.intervention_terms) == 1


# ---------------------------------------------------------------------------
# 11. No MeSH generation
# ---------------------------------------------------------------------------

def test_no_mesh_terms_generated():
    strategy = _pico_strategy(intervention_terms=["Metformin"])
    combined = " ".join(strategy.intervention_terms)
    assert "[MeSH]" not in combined
    assert "[mh]" not in combined.lower()


def test_strategy_has_no_mesh_attribute():
    strategy = _pico_strategy()
    assert not hasattr(strategy, "mesh_terms")
    assert not hasattr(strategy, "mesh_headings")


# ---------------------------------------------------------------------------
# 12. No automatic query construction
# ---------------------------------------------------------------------------

def test_boolean_query_not_auto_constructed_when_none():
    strategy = LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        population_terms=["Adults"],
        intervention_terms=["Drug A"],
    )
    assert strategy.boolean_query is None


def test_strategy_has_no_build_query_method():
    strategy = _pico_strategy()
    assert not callable(getattr(strategy, "build_query", None))
    assert not callable(getattr(strategy, "construct_query", None))
    assert not callable(getattr(strategy, "execute", None))


# ---------------------------------------------------------------------------
# 13. Strategy cannot be mutated after creation
# ---------------------------------------------------------------------------

def test_population_terms_immutable():
    strategy = _pico_strategy()
    with pytest.raises(Exception):
        strategy.population_terms = ["mutated"]


def test_intervention_terms_immutable():
    strategy = _pico_strategy()
    with pytest.raises(Exception):
        strategy.intervention_terms = ["mutated"]


def test_boolean_query_immutable():
    strategy = _pico_strategy(boolean_query="original query")
    with pytest.raises(Exception):
        strategy.boolean_query = "mutated query"


def test_framework_type_immutable():
    strategy = _pico_strategy()
    with pytest.raises(Exception):
        strategy.framework_type = FrameworkType.PECO


def test_outcome_terms_immutable():
    strategy = _pico_strategy()
    with pytest.raises(Exception):
        strategy.outcome_terms = ["mutated"]


# ---------------------------------------------------------------------------
# 14. No external API called
# ---------------------------------------------------------------------------

def test_no_http_calls_on_creation(monkeypatch):
    import urllib.request
    called = []
    original = urllib.request.urlopen

    def mock_urlopen(*args, **kwargs):
        called.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    _pico_strategy()
    assert called == []


# ---------------------------------------------------------------------------
# 15. No AI called
# ---------------------------------------------------------------------------

def test_strategy_has_no_ai_methods():
    strategy = _pico_strategy()
    for forbidden in ("generate", "expand", "suggest", "infer", "ai_complete"):
        assert not callable(getattr(strategy, forbidden, None))


# ---------------------------------------------------------------------------
# Public API import
# ---------------------------------------------------------------------------

def test_literature_search_strategy_importable_from_domain():
    from domain import LiteratureSearchStrategy
    assert LiteratureSearchStrategy is not None


def test_literature_search_strategy_in_domain_all():
    import domain
    assert "LiteratureSearchStrategy" in domain.__all__


# ---------------------------------------------------------------------------
# PECO-specific — exposure terms independent from intervention
# ---------------------------------------------------------------------------

def test_peco_strategy_exposure_terms_independent():
    strategy = _peco_strategy()
    assert strategy.exposure_terms == ["Cigarette smoking"]
    assert strategy.intervention_terms == []


def test_pico_strategy_intervention_terms_independent():
    strategy = _pico_strategy()
    assert strategy.intervention_terms == ["Metformin"]
    assert strategy.exposure_terms == []
