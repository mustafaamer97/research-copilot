"""Tests for the canonical literature source adapter contract."""
import inspect
import pytest
from abc import ABC
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from domain.framework import FrameworkType
from domain.literature import ExternalSource, LiteratureRecord
from domain.literature_search import LiteratureSearchStrategy
from services.literature_source import (
    LiteratureSearchResult,
    LiteratureSourceAdapter,
    LiteratureSourceError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _strategy() -> LiteratureSearchStrategy:
    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        population_terms=["Adults"],
        intervention_terms=["Drug A"],
        comparator_terms=["Placebo"],
        outcome_terms=["Mortality"],
        boolean_query='("Adults") AND ("Drug A") AND ("Placebo") AND ("Mortality")',
    )


def _record() -> LiteratureRecord:
    return LiteratureRecord(
        title="Effect of Drug A on Mortality",
        authors=["Smith J"],
        source=ExternalSource.PUBMED,
        source_record_id="PMC999888",
        retrieved_at=_utc_now(),
    )


def _result(**kwargs) -> LiteratureSearchResult:
    defaults = dict(
        source=ExternalSource.PUBMED,
        records=[_record()],
        retrieved_at=_utc_now(),
        query='("Adults") AND ("Drug A")',
    )
    defaults.update(kwargs)
    return LiteratureSearchResult(**defaults)


# ---------------------------------------------------------------------------
# Concrete test adapter
# ---------------------------------------------------------------------------

class _ConcreteAdapter(LiteratureSourceAdapter):
    def __init__(self, result: LiteratureSearchResult) -> None:
        self._result = result

    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        return self._result


class _ErrorAdapter(LiteratureSourceAdapter):
    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        raise LiteratureSourceError(ExternalSource.PUBMED, "Connection refused.")


# ---------------------------------------------------------------------------
# 1. Valid LiteratureSearchResult can be created
# ---------------------------------------------------------------------------

def test_valid_result_can_be_created():
    result = _result()
    assert result is not None


def test_result_source_is_set():
    result = _result(source=ExternalSource.PUBMED)
    assert result.source == ExternalSource.PUBMED


# ---------------------------------------------------------------------------
# 2. Correct ExternalSource is preserved
# ---------------------------------------------------------------------------

def test_pubmed_source_preserved():
    result = _result(source=ExternalSource.PUBMED)
    assert result.source == ExternalSource.PUBMED


def test_europe_pmc_source_preserved():
    result = _result(source=ExternalSource.EUROPE_PMC)
    assert result.source == ExternalSource.EUROPE_PMC


def test_openalex_source_preserved():
    result = _result(source=ExternalSource.OPENALEX)
    assert result.source == ExternalSource.OPENALEX


def test_crossref_source_preserved():
    result = _result(source=ExternalSource.CROSSREF)
    assert result.source == ExternalSource.CROSSREF


# ---------------------------------------------------------------------------
# 3. LiteratureRecord objects are preserved
# ---------------------------------------------------------------------------

def test_records_are_preserved():
    rec = _record()
    result = _result(records=[rec])
    assert len(result.records) == 1
    assert result.records[0].title == rec.title


def test_multiple_records_preserved():
    r1 = LiteratureRecord(
        title="Study One",
        source=ExternalSource.PUBMED,
        source_record_id="PMC001",
        retrieved_at=_utc_now(),
    )
    r2 = LiteratureRecord(
        title="Study Two",
        source=ExternalSource.PUBMED,
        source_record_id="PMC002",
        retrieved_at=_utc_now(),
    )
    result = _result(records=[r1, r2])
    assert len(result.records) == 2
    assert result.records[0].source_record_id == "PMC001"
    assert result.records[1].source_record_id == "PMC002"


def test_records_contain_literature_record_instances():
    result = _result()
    for rec in result.records:
        assert isinstance(rec, LiteratureRecord)


# ---------------------------------------------------------------------------
# 4. Empty records are valid
# ---------------------------------------------------------------------------

def test_empty_records_are_valid():
    result = _result(records=[])
    assert result.records == []


def test_empty_result_is_not_an_error():
    result = _result(records=[])
    assert result is not None


# ---------------------------------------------------------------------------
# 5. Query is preserved exactly
# ---------------------------------------------------------------------------

def test_query_preserved_exactly():
    query = '("Adults") AND ("Drug A") AND ("Placebo") AND ("Mortality")'
    result = _result(query=query)
    assert result.query == query


def test_query_not_modified():
    query = "raw query string with (parens) and OR AND special chars"
    result = _result(query=query)
    assert result.query == query


# ---------------------------------------------------------------------------
# 6. retrieved_at accepts timezone-aware UTC
# ---------------------------------------------------------------------------

def test_utc_retrieved_at_accepted():
    result = _result(retrieved_at=datetime.now(timezone.utc))
    assert result.retrieved_at.tzinfo is not None


def test_non_utc_aware_retrieved_at_accepted():
    tz = timezone(timedelta(hours=3))
    result = _result(retrieved_at=datetime.now(tz))
    assert result.retrieved_at.tzinfo is not None


# ---------------------------------------------------------------------------
# 7. Naive retrieved_at is rejected
# ---------------------------------------------------------------------------

def test_naive_retrieved_at_rejected():
    with pytest.raises(Exception):
        _result(retrieved_at=datetime(2023, 6, 15, 12, 0, 0))


# ---------------------------------------------------------------------------
# 8. Result cannot be mutated
# ---------------------------------------------------------------------------

def test_result_source_immutable():
    result = _result()
    with pytest.raises(Exception):
        result.source = ExternalSource.CROSSREF


def test_result_records_immutable():
    result = _result()
    with pytest.raises(Exception):
        result.records = []


def test_result_query_immutable():
    result = _result()
    with pytest.raises(Exception):
        result.query = "mutated query"


def test_result_retrieved_at_immutable():
    result = _result()
    with pytest.raises(Exception):
        result.retrieved_at = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# 9. LiteratureSourceAdapter exists
# ---------------------------------------------------------------------------

def test_literature_source_adapter_exists():
    assert LiteratureSourceAdapter is not None


def test_literature_source_adapter_is_abstract():
    assert issubclass(LiteratureSourceAdapter, ABC)


# ---------------------------------------------------------------------------
# 10. It defines search()
# ---------------------------------------------------------------------------

def test_adapter_defines_search_method():
    assert hasattr(LiteratureSourceAdapter, "search")
    assert callable(LiteratureSourceAdapter.search)


def test_search_is_abstract():
    abstract_methods = getattr(LiteratureSourceAdapter, "__abstractmethods__", set())
    assert "search" in abstract_methods


# ---------------------------------------------------------------------------
# 11. search() requires LiteratureSearchStrategy
# ---------------------------------------------------------------------------

def test_search_signature_accepts_strategy():
    sig = inspect.signature(LiteratureSourceAdapter.search)
    params = list(sig.parameters.keys())
    assert "strategy" in params


# ---------------------------------------------------------------------------
# 12. A concrete test adapter can implement the contract
# ---------------------------------------------------------------------------

def test_concrete_adapter_can_be_instantiated():
    adapter = _ConcreteAdapter(result=_result())
    assert adapter is not None


def test_concrete_adapter_is_instance_of_base():
    adapter = _ConcreteAdapter(result=_result())
    assert isinstance(adapter, LiteratureSourceAdapter)


# ---------------------------------------------------------------------------
# 13. A concrete adapter can return LiteratureSearchResult
# ---------------------------------------------------------------------------

def test_concrete_adapter_search_returns_result():
    expected = _result()
    adapter = _ConcreteAdapter(result=expected)
    returned = adapter.search(_strategy())
    assert isinstance(returned, LiteratureSearchResult)


def test_concrete_adapter_search_preserves_records():
    rec = _record()
    expected = _result(records=[rec])
    adapter = _ConcreteAdapter(result=expected)
    returned = adapter.search(_strategy())
    assert len(returned.records) == 1
    assert returned.records[0].title == rec.title


def test_concrete_adapter_does_not_mutate_strategy():
    strategy = _strategy()
    original_query = strategy.boolean_query
    adapter = _ConcreteAdapter(result=_result())
    adapter.search(strategy)
    assert strategy.boolean_query == original_query


# ---------------------------------------------------------------------------
# 14. The base contract does not perform network calls
# ---------------------------------------------------------------------------

def test_base_contract_has_no_network_imports():
    source = inspect.getsource(
        __import__("services.literature_source", fromlist=["literature_source"])
    )
    assert "requests" not in source
    assert "aiohttp" not in source
    assert "urllib.request.urlopen" not in source
    assert "httpx" not in source


# ---------------------------------------------------------------------------
# 15. LiteratureSourceError exists
# ---------------------------------------------------------------------------

def test_literature_source_error_exists():
    assert LiteratureSourceError is not None


def test_literature_source_error_is_exception():
    assert issubclass(LiteratureSourceError, Exception)


# ---------------------------------------------------------------------------
# 16. LiteratureSourceError can be raised and caught
# ---------------------------------------------------------------------------

def test_literature_source_error_can_be_raised():
    with pytest.raises(LiteratureSourceError):
        raise LiteratureSourceError(ExternalSource.PUBMED, "Timeout.")


def test_literature_source_error_carries_source():
    try:
        raise LiteratureSourceError(ExternalSource.EUROPE_PMC, "Rate limited.")
    except LiteratureSourceError as e:
        assert e.source == ExternalSource.EUROPE_PMC


def test_literature_source_error_carries_message():
    try:
        raise LiteratureSourceError(ExternalSource.PUBMED, "Service unavailable.")
    except LiteratureSourceError as e:
        assert "Service unavailable." in e.message


def test_error_adapter_raises_literature_source_error():
    adapter = _ErrorAdapter()
    with pytest.raises(LiteratureSourceError):
        adapter.search(_strategy())


# ---------------------------------------------------------------------------
# 17. No external API called
# ---------------------------------------------------------------------------

def test_no_http_calls_on_result_creation(monkeypatch):
    import urllib.request
    called = []
    original = urllib.request.urlopen

    def mock_urlopen(*args, **kwargs):
        called.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    _result()
    assert called == []


# ---------------------------------------------------------------------------
# 18. No AI called
# ---------------------------------------------------------------------------

def test_no_ai_imports_in_source_module():
    import services.literature_source as mod
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


# ---------------------------------------------------------------------------
# 19. No HTTP library imported
# ---------------------------------------------------------------------------

def test_no_http_library_in_source_module():
    import services.literature_source as mod
    source = inspect.getsource(mod)
    assert "import requests" not in source
    assert "import aiohttp" not in source
    assert "import httpx" not in source


# ---------------------------------------------------------------------------
# Public imports
# ---------------------------------------------------------------------------

def test_literature_source_adapter_importable_from_services():
    from services import LiteratureSourceAdapter
    assert LiteratureSourceAdapter is not None


def test_literature_search_result_importable_from_services():
    from services import LiteratureSearchResult
    assert LiteratureSearchResult is not None


def test_literature_source_error_importable_from_services():
    from services import LiteratureSourceError
    assert issubclass(LiteratureSourceError, Exception)
