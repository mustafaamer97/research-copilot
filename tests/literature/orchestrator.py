"""Tests for LiteratureSearchOrchestrator — fully offline."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from domain.framework import FrameworkType
from domain.literature import ExternalSource, LiteratureRecord
from domain.literature_search import LiteratureSearchStrategy
from literature.orchestrator import (
    LiteratureSearchCollection,
    LiteratureSearchOrchestrator,
    SourceFailure,
)
from services.literature_source import (
    LiteratureSearchResult,
    LiteratureSourceAdapter,
    LiteratureSourceError,
)


# ---------------------------------------------------------------------------
# Helpers — fake adapters
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _strategy(query: str = '("Metformin") AND ("type 2 diabetes")') -> LiteratureSearchStrategy:
    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        population_terms=["Adults"],
        intervention_terms=["Metformin"],
        comparator_terms=["Placebo"],
        outcome_terms=["Mortality"],
        boolean_query=query,
    )


def _record(source: ExternalSource, title: str = "A Study") -> LiteratureRecord:
    return LiteratureRecord(
        title=title,
        source=source,
        source_record_id=str(uuid4()),
        retrieved_at=_utc_now(),
    )


def _result(
    source: ExternalSource,
    records: list[LiteratureRecord] | None = None,
    query: str = '("Metformin") AND ("type 2 diabetes")',
) -> LiteratureSearchResult:
    return LiteratureSearchResult(
        source=source,
        records=records if records is not None else [_record(source)],
        retrieved_at=_utc_now(),
        query=query,
    )


class _FakeAdapter(LiteratureSourceAdapter):
    """Returns a fixed result. Records which strategy it received."""

    def __init__(
        self,
        result: LiteratureSearchResult,
        name: str = "FakeAdapter",
    ) -> None:
        self._result = result
        self.name = name
        self.received_strategies: list[LiteratureSearchStrategy] = []

    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        self.received_strategies.append(strategy)
        return self._result


class _FailingAdapter(LiteratureSourceAdapter):
    """Always raises LiteratureSourceError."""

    def __init__(self, source: ExternalSource = ExternalSource.OPENALEX) -> None:
        self._source = source
        self.received_strategies: list[LiteratureSearchStrategy] = []

    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        self.received_strategies.append(strategy)
        raise LiteratureSourceError(self._source, "Simulated failure.")


class _EmptyAdapter(LiteratureSourceAdapter):
    """Returns zero records."""

    def __init__(self, source: ExternalSource) -> None:
        self._source = source
        self.received_strategies: list[LiteratureSearchStrategy] = []

    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        self.received_strategies.append(strategy)
        return LiteratureSearchResult(
            source=self._source,
            records=[],
            retrieved_at=_utc_now(),
            query=strategy.boolean_query or "",
        )


# ---------------------------------------------------------------------------
# 1. Basic construction and empty adapter list
# ---------------------------------------------------------------------------

def test_orchestrator_can_be_constructed():
    orch = LiteratureSearchOrchestrator(adapters=[])
    assert orch is not None


def test_empty_adapters_returns_empty_collection():
    orch = LiteratureSearchOrchestrator(adapters=[])
    collection = orch.search(_strategy())
    assert isinstance(collection, LiteratureSearchCollection)
    assert collection.results == []
    assert collection.failures == []


def test_empty_adapters_no_error():
    orch = LiteratureSearchOrchestrator(adapters=[])
    collection = orch.search(_strategy())
    assert collection.total_records == 0


# ---------------------------------------------------------------------------
# 2. Single adapter
# ---------------------------------------------------------------------------

def test_single_adapter_returns_one_result():
    adapter = _FakeAdapter(_result(ExternalSource.PUBMED))
    orch = LiteratureSearchOrchestrator(adapters=[adapter])
    collection = orch.search(_strategy())
    assert len(collection.results) == 1


def test_single_adapter_result_source_preserved():
    result = _result(ExternalSource.PUBMED)
    adapter = _FakeAdapter(result)
    orch = LiteratureSearchOrchestrator(adapters=[adapter])
    collection = orch.search(_strategy())
    assert collection.results[0].source == ExternalSource.PUBMED


def test_single_adapter_records_preserved():
    rec = _record(ExternalSource.PUBMED, "Specific Study Title")
    result = _result(ExternalSource.PUBMED, records=[rec])
    adapter = _FakeAdapter(result)
    orch = LiteratureSearchOrchestrator(adapters=[adapter])
    collection = orch.search(_strategy())
    assert len(collection.results[0].records) == 1
    assert collection.results[0].records[0].title == "Specific Study Title"


# ---------------------------------------------------------------------------
# 3. Multiple adapters — all succeed
# ---------------------------------------------------------------------------

def test_multiple_adapters_returns_all_results():
    adapters = [
        _FakeAdapter(_result(ExternalSource.PUBMED), name="A"),
        _FakeAdapter(_result(ExternalSource.EUROPE_PMC), name="B"),
        _FakeAdapter(_result(ExternalSource.OPENALEX), name="C"),
    ]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    collection = orch.search(_strategy())
    assert len(collection.results) == 3


def test_multiple_adapters_sources_correct():
    adapters = [
        _FakeAdapter(_result(ExternalSource.PUBMED)),
        _FakeAdapter(_result(ExternalSource.EUROPE_PMC)),
        _FakeAdapter(_result(ExternalSource.OPENALEX)),
    ]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    collection = orch.search(_strategy())
    sources = [r.source for r in collection.results]
    assert ExternalSource.PUBMED in sources
    assert ExternalSource.EUROPE_PMC in sources
    assert ExternalSource.OPENALEX in sources


def test_four_adapters_four_results():
    adapters = [
        _FakeAdapter(_result(ExternalSource.PUBMED)),
        _FakeAdapter(_result(ExternalSource.EUROPE_PMC)),
        _FakeAdapter(_result(ExternalSource.OPENALEX)),
        _FakeAdapter(_result(ExternalSource.CROSSREF)),
    ]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    collection = orch.search(_strategy())
    assert len(collection.results) == 4
    assert len(collection.failures) == 0


# ---------------------------------------------------------------------------
# 4. Same strategy passed to every adapter
# ---------------------------------------------------------------------------

def test_every_adapter_receives_same_strategy_instance():
    strategy = _strategy()
    adapters = [
        _FakeAdapter(_result(ExternalSource.PUBMED), name="A"),
        _FakeAdapter(_result(ExternalSource.EUROPE_PMC), name="B"),
        _FakeAdapter(_result(ExternalSource.OPENALEX), name="C"),
    ]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    orch.search(strategy)

    for adapter in adapters:
        assert len(adapter.received_strategies) == 1
        assert adapter.received_strategies[0] is strategy


def test_strategy_not_mutated_by_orchestrator():
    strategy = _strategy(query='("Aspirin") AND ("stroke")')
    original_query = strategy.boolean_query
    adapters = [
        _FakeAdapter(_result(ExternalSource.PUBMED)),
        _FakeAdapter(_result(ExternalSource.EUROPE_PMC)),
    ]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    orch.search(strategy)
    assert strategy.boolean_query == original_query


def test_all_adapters_receive_same_query():
    query = '("Metformin") AND ("type 2 diabetes")'
    strategy = _strategy(query=query)
    adapters = [
        _FakeAdapter(_result(ExternalSource.PUBMED)),
        _FakeAdapter(_result(ExternalSource.EUROPE_PMC)),
        _FakeAdapter(_result(ExternalSource.OPENALEX)),
        _FakeAdapter(_result(ExternalSource.CROSSREF)),
    ]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    orch.search(strategy)

    for adapter in adapters:
        received = adapter.received_strategies[0]
        assert received.boolean_query == query


# ---------------------------------------------------------------------------
# 5. Order preservation
# ---------------------------------------------------------------------------

def test_result_order_matches_adapter_order():
    a1 = _FakeAdapter(_result(ExternalSource.CROSSREF), name="Crossref")
    a2 = _FakeAdapter(_result(ExternalSource.PUBMED), name="PubMed")
    a3 = _FakeAdapter(_result(ExternalSource.OPENALEX), name="OpenAlex")
    a4 = _FakeAdapter(_result(ExternalSource.EUROPE_PMC), name="EuropePMC")

    orch = LiteratureSearchOrchestrator(adapters=[a1, a2, a3, a4])
    collection = orch.search(_strategy())

    assert collection.results[0].source == ExternalSource.CROSSREF
    assert collection.results[1].source == ExternalSource.PUBMED
    assert collection.results[2].source == ExternalSource.OPENALEX
    assert collection.results[3].source == ExternalSource.EUROPE_PMC


def test_deliberate_order_preserved():
    sources = [
        ExternalSource.OPENALEX,
        ExternalSource.CROSSREF,
        ExternalSource.EUROPE_PMC,
        ExternalSource.PUBMED,
    ]
    adapters = [_FakeAdapter(_result(s)) for s in sources]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    collection = orch.search(_strategy())

    result_sources = [r.source for r in collection.results]
    assert result_sources == sources


# ---------------------------------------------------------------------------
# 6. Empty source result preserved
# ---------------------------------------------------------------------------

def test_empty_source_result_preserved():
    empty = _EmptyAdapter(ExternalSource.PUBMED)
    populated = _FakeAdapter(_result(ExternalSource.EUROPE_PMC))
    orch = LiteratureSearchOrchestrator(adapters=[empty, populated])
    collection = orch.search(_strategy())
    assert len(collection.results) == 2
    assert collection.results[0].records == []
    assert len(collection.results[1].records) == 1


def test_empty_adapter_result_source_preserved():
    empty = _EmptyAdapter(ExternalSource.CROSSREF)
    orch = LiteratureSearchOrchestrator(adapters=[empty])
    collection = orch.search(_strategy())
    assert collection.results[0].source == ExternalSource.CROSSREF
    assert collection.results[0].records == []


# ---------------------------------------------------------------------------
# 7. No deduplication
# ---------------------------------------------------------------------------

def test_identical_records_from_multiple_adapters_all_preserved():
    rec = _record(ExternalSource.PUBMED, "Shared Study")
    # Create equivalent records from three sources
    r1 = LiteratureSearchResult(
        source=ExternalSource.PUBMED,
        records=[rec],
        retrieved_at=_utc_now(),
        query="query",
    )
    r2 = LiteratureSearchResult(
        source=ExternalSource.EUROPE_PMC,
        records=[_record(ExternalSource.EUROPE_PMC, "Shared Study")],
        retrieved_at=_utc_now(),
        query="query",
    )
    r3 = LiteratureSearchResult(
        source=ExternalSource.OPENALEX,
        records=[_record(ExternalSource.OPENALEX, "Shared Study")],
        retrieved_at=_utc_now(),
        query="query",
    )
    adapters = [
        _FakeAdapter(r1),
        _FakeAdapter(r2),
        _FakeAdapter(r3),
    ]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    collection = orch.search(_strategy())
    assert collection.total_records == 3


def test_all_records_flat_list_contains_all():
    r1 = _result(ExternalSource.PUBMED, records=[
        _record(ExternalSource.PUBMED, "Study A"),
        _record(ExternalSource.PUBMED, "Study B"),
    ])
    r2 = _result(ExternalSource.EUROPE_PMC, records=[
        _record(ExternalSource.EUROPE_PMC, "Study A"),
    ])
    orch = LiteratureSearchOrchestrator(adapters=[_FakeAdapter(r1), _FakeAdapter(r2)])
    collection = orch.search(_strategy())
    assert len(collection.all_records) == 3


# ---------------------------------------------------------------------------
# 8. Partial failure
# ---------------------------------------------------------------------------

def test_partial_failure_successful_results_preserved():
    success_a = _FakeAdapter(_result(ExternalSource.PUBMED), name="PubMed")
    failing = _FailingAdapter(ExternalSource.OPENALEX)
    success_b = _FakeAdapter(_result(ExternalSource.CROSSREF), name="Crossref")

    orch = LiteratureSearchOrchestrator(adapters=[success_a, failing, success_b])
    collection = orch.search(_strategy())

    assert len(collection.results) == 2
    sources = [r.source for r in collection.results]
    assert ExternalSource.PUBMED in sources
    assert ExternalSource.CROSSREF in sources


def test_partial_failure_failure_recorded():
    success = _FakeAdapter(_result(ExternalSource.PUBMED))
    failing = _FailingAdapter(ExternalSource.OPENALEX)

    orch = LiteratureSearchOrchestrator(adapters=[success, failing])
    collection = orch.search(_strategy())

    assert len(collection.failures) == 1
    assert collection.failures[0].error.source == ExternalSource.OPENALEX


def test_partial_failure_has_failures_flag():
    failing = _FailingAdapter(ExternalSource.EUROPE_PMC)
    orch = LiteratureSearchOrchestrator(adapters=[failing])
    collection = orch.search(_strategy())
    assert collection.has_failures is True


def test_no_failures_has_failures_false():
    adapter = _FakeAdapter(_result(ExternalSource.PUBMED))
    orch = LiteratureSearchOrchestrator(adapters=[adapter])
    collection = orch.search(_strategy())
    assert collection.has_failures is False


def test_failure_adapter_name_recorded():
    class _NamedFailingAdapter(LiteratureSourceAdapter):
        def search(self, strategy):
            raise LiteratureSourceError(ExternalSource.OPENALEX, "Error.")

    orch = LiteratureSearchOrchestrator(adapters=[_NamedFailingAdapter()])
    collection = orch.search(_strategy())
    assert collection.failures[0].adapter_name == "_NamedFailingAdapter"


def test_all_failing_returns_empty_results_all_failures():
    adapters = [
        _FailingAdapter(ExternalSource.PUBMED),
        _FailingAdapter(ExternalSource.EUROPE_PMC),
    ]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    collection = orch.search(_strategy())
    assert collection.results == []
    assert len(collection.failures) == 2


def test_success_results_not_discarded_when_one_fails():
    a = _FakeAdapter(_result(ExternalSource.PUBMED))
    b = _FailingAdapter(ExternalSource.EUROPE_PMC)
    c = _FakeAdapter(_result(ExternalSource.CROSSREF))
    d = _FailingAdapter(ExternalSource.OPENALEX)

    orch = LiteratureSearchOrchestrator(adapters=[a, b, c, d])
    collection = orch.search(_strategy())
    assert len(collection.results) == 2
    assert len(collection.failures) == 2


# ---------------------------------------------------------------------------
# 9. Query preservation
# ---------------------------------------------------------------------------

def test_query_preserved_in_all_results():
    query = '("Metformin") AND ("type 2 diabetes")'
    strategy = _strategy(query=query)
    adapters = [
        _FakeAdapter(_result(ExternalSource.PUBMED, query=query)),
        _FakeAdapter(_result(ExternalSource.EUROPE_PMC, query=query)),
    ]
    orch = LiteratureSearchOrchestrator(adapters=adapters)
    collection = orch.search(strategy)

    for r in collection.results:
        assert r.query == query


# ---------------------------------------------------------------------------
# 10. all_records and total_records helpers
# ---------------------------------------------------------------------------

def test_total_records_sums_all_sources():
    r1 = _result(ExternalSource.PUBMED, records=[
        _record(ExternalSource.PUBMED),
        _record(ExternalSource.PUBMED),
    ])
    r2 = _result(ExternalSource.EUROPE_PMC, records=[
        _record(ExternalSource.EUROPE_PMC),
    ])
    orch = LiteratureSearchOrchestrator(adapters=[_FakeAdapter(r1), _FakeAdapter(r2)])
    collection = orch.search(_strategy())
    assert collection.total_records == 3


def test_all_records_empty_when_no_adapters():
    orch = LiteratureSearchOrchestrator(adapters=[])
    collection = orch.search(_strategy())
    assert collection.all_records == []


def test_all_records_includes_all_sources():
    r1 = _result(ExternalSource.PUBMED, records=[_record(ExternalSource.PUBMED, "P")])
    r2 = _result(ExternalSource.CROSSREF, records=[_record(ExternalSource.CROSSREF, "C")])
    orch = LiteratureSearchOrchestrator(adapters=[_FakeAdapter(r1), _FakeAdapter(r2)])
    collection = orch.search(_strategy())
    titles = [rec.title for rec in collection.all_records]
    assert "P" in titles
    assert "C" in titles


# ---------------------------------------------------------------------------
# 11. No AI or external calls
# ---------------------------------------------------------------------------

def test_no_ai_imports_in_orchestrator():
    import inspect
    import literature.orchestrator as mod
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


def test_no_http_imports_in_orchestrator():
    import inspect
    import literature.orchestrator as mod
    source = inspect.getsource(mod)
    assert "urllib.request.urlopen" not in source
    assert "requests" not in source
    assert "aiohttp" not in source


def test_no_concrete_adapter_imports_in_orchestrator():
    import inspect
    import literature.orchestrator as mod
    source = inspect.getsource(mod)
    assert "PubMedAdapter" not in source
    assert "EuropePMCAdapter" not in source
    assert "OpenAlexAdapter" not in source
    assert "CrossrefAdapter" not in source


# ---------------------------------------------------------------------------
# 12. Public import
# ---------------------------------------------------------------------------

def test_orchestrator_importable_from_literature():
    from literature import LiteratureSearchOrchestrator
    assert LiteratureSearchOrchestrator is not None


def test_collection_importable_from_literature():
    from literature import LiteratureSearchCollection
    assert LiteratureSearchCollection is not None


def test_source_failure_importable_from_literature():
    from literature import SourceFailure
    assert SourceFailure is not None
