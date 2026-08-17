"""Tests for EuropePMCAdapter — all HTTP is mocked; no live network calls."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from adapters.europe_pmc import EuropePMCAdapter, _DEFAULT_MAX_RESULTS
from domain.framework import FrameworkType
from domain.literature import ExternalSource, LiteratureRecord
from domain.literature_search import LiteratureSearchStrategy
from services.literature_source import (
    LiteratureSearchResult,
    LiteratureSourceAdapter,
    LiteratureSourceError,
)


# ---------------------------------------------------------------------------
# JSON fixtures
# ---------------------------------------------------------------------------

def _make_response(results: list[dict]) -> bytes:
    return json.dumps({"resultList": {"result": results}}).encode()


_FULL_RESULT = {
    "id": "33100000",
    "source": "MED",
    "title": "Effect of Metformin on Cardiovascular Outcomes",
    "authorList": {
        "author": [
            {"lastName": "Smith", "firstName": "Jane", "initials": "J"},
            {"lastName": "Brown", "firstName": "Alex", "initials": "A"},
        ]
    },
    "journalTitle": "Journal of Endocrinology",
    "firstPublicationDate": "2023-04-10",
    "abstractText": "Background: This study examined metformin in T2DM patients.",
    "doi": "10.9999/metformin.study",
    "pmid": "33100000",
}

_NO_DOI_RESULT = {
    "id": "44200000",
    "source": "MED",
    "title": "Smoking and Lung Cancer: A Cohort Study",
    "authorList": {"author": []},
    "journalTitle": "Respiratory Medicine",
    "firstPublicationDate": "2022-01-15",
    "pmid": "44200000",
}

_NO_PMID_RESULT = {
    "id": "PPR-999",
    "source": "PPR",
    "title": "Preprint: Novel Findings in Oncology",
    "authorString": "Williams K, Davies P",
    "journalTitle": "bioRxiv",
    "firstPublicationDate": "2023-11-01",
    "doi": "10.1101/2023.11.01.12345",
}

_NO_ABSTRACT_RESULT = {
    "id": "55300000",
    "source": "MED",
    "title": "Brief Communication Without Abstract",
    "authorList": {"author": [{"lastName": "Taylor", "firstName": "C"}]},
    "journalTitle": "Brief Reports",
    "firstPublicationDate": "2021-06-01",
    "pmid": "55300000",
}

_NO_AUTHORS_RESULT = {
    "id": "66400000",
    "source": "MED",
    "title": "Consensus Statement on Hypertension Management",
    "journalTitle": "Guidelines Today",
    "firstPublicationDate": "2020-03-22",
    "pmid": "66400000",
}

_NO_PUBDATE_RESULT = {
    "id": "77500000",
    "source": "MED",
    "title": "Article With No Publication Date",
    "authorList": {"author": [{"lastName": "Green", "firstName": "R"}]},
    "journalTitle": "Undated Review",
    "pmid": "77500000",
}

_ZERO_RESULTS_RESPONSE = _make_response([])
_MALFORMED_JSON = b"not json <<{"
_EMPTY_RESULT_LIST = json.dumps({"resultList": {"result": []}}).encode()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strategy(
    query: str = '("Metformin") AND ("type 2 diabetes")',
) -> LiteratureSearchStrategy:
    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        population_terms=["Adults with type 2 diabetes"],
        intervention_terms=["Metformin"],
        comparator_terms=["Placebo"],
        outcome_terms=["Cardiovascular mortality"],
        boolean_query=query,
    )


def _adapter(**kwargs) -> EuropePMCAdapter:
    return EuropePMCAdapter(**kwargs)


def _mock_response(body: bytes):
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _patch_urlopen(body: bytes):
    return patch(
        "urllib.request.urlopen",
        return_value=_mock_response(body),
    )


def _patch_urlopen_seq(responses: list[bytes]):
    calls = iter(responses)

    def _side(req, timeout=None):
        return _mock_response(next(calls))

    return patch("urllib.request.urlopen", side_effect=_side)


# ---------------------------------------------------------------------------
# 1. Successful search returns result
# ---------------------------------------------------------------------------

def test_successful_search_returns_result():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert isinstance(result, LiteratureSearchResult)


def test_successful_search_source_is_europe_pmc():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.source == ExternalSource.EUROPE_PMC


def test_successful_search_returns_one_record():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert len(result.records) == 1


def test_result_retrieved_at_is_utc():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.retrieved_at.tzinfo is not None


# ---------------------------------------------------------------------------
# 2. Full record mapping
# ---------------------------------------------------------------------------

def test_full_record_source_record_id():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].source_record_id == "33100000"


def test_full_record_source_is_europe_pmc():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].source == ExternalSource.EUROPE_PMC


def test_full_record_title():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].title == "Effect of Metformin on Cardiovascular Outcomes"


def test_full_record_authors():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    authors = result.records[0].authors
    assert any("Smith" in a for a in authors)
    assert any("Brown" in a for a in authors)


def test_full_record_journal():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].journal == "Journal of Endocrinology"


def test_full_record_publication_date():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date == "2023-04-10"


def test_full_record_abstract():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is not None
    assert "metformin" in result.records[0].abstract.lower()


def test_full_record_doi():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].doi == "10.9999/metformin.study"


def test_full_record_pmid():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid == "33100000"


def test_full_record_source_url_contains_id():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert "33100000" in result.records[0].source_url


def test_full_record_source_url_contains_europepmc():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert "europepmc.org" in result.records[0].source_url


# ---------------------------------------------------------------------------
# 3. Missing DOI → None
# ---------------------------------------------------------------------------

def test_missing_doi_is_none():
    with _patch_urlopen(_make_response([_NO_DOI_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].doi is None


# ---------------------------------------------------------------------------
# 4. Missing PMID → None
# ---------------------------------------------------------------------------

def test_missing_pmid_is_none():
    with _patch_urlopen(_make_response([_NO_PMID_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid is None


def test_missing_pmid_source_record_id_still_set():
    with _patch_urlopen(_make_response([_NO_PMID_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].source_record_id == "PPR-999"


# ---------------------------------------------------------------------------
# 5. Missing abstract → None
# ---------------------------------------------------------------------------

def test_missing_abstract_is_none():
    with _patch_urlopen(_make_response([_NO_ABSTRACT_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is None


# ---------------------------------------------------------------------------
# 6. Missing authors → empty list
# ---------------------------------------------------------------------------

def test_missing_authors_returns_empty_list():
    with _patch_urlopen(_make_response([_NO_AUTHORS_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].authors == []


# ---------------------------------------------------------------------------
# 7. Missing publication date → None
# ---------------------------------------------------------------------------

def test_missing_pub_date_is_none():
    with _patch_urlopen(_make_response([_NO_PUBDATE_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date is None


# ---------------------------------------------------------------------------
# 8. authorString fallback
# ---------------------------------------------------------------------------

def test_author_string_fallback_used():
    with _patch_urlopen(_make_response([_NO_PMID_RESULT])):
        result = _adapter().search(_strategy())
    authors = result.records[0].authors
    assert any("Williams" in a for a in authors)
    assert any("Davies" in a for a in authors)


# ---------------------------------------------------------------------------
# 9. Zero results
# ---------------------------------------------------------------------------

def test_zero_results_returns_empty_records():
    with _patch_urlopen(_ZERO_RESULTS_RESPONSE):
        result = _adapter().search(_strategy())
    assert result.records == []


def test_zero_results_is_not_an_error():
    with _patch_urlopen(_ZERO_RESULTS_RESPONSE):
        result = _adapter().search(_strategy())
    assert result is not None


def test_empty_result_list_field():
    with _patch_urlopen(_EMPTY_RESULT_LIST):
        result = _adapter().search(_strategy())
    assert result.records == []


# ---------------------------------------------------------------------------
# 10. Multiple records
# ---------------------------------------------------------------------------

def test_multiple_records_returned():
    with _patch_urlopen(_make_response([_FULL_RESULT, _NO_DOI_RESULT])):
        result = _adapter().search(_strategy())
    assert len(result.records) == 2


def test_multiple_records_are_literature_record_instances():
    with _patch_urlopen(_make_response([_FULL_RESULT, _NO_DOI_RESULT])):
        result = _adapter().search(_strategy())
    for rec in result.records:
        assert isinstance(rec, LiteratureRecord)


# ---------------------------------------------------------------------------
# 11. Query integrity — exact query reaches API
# ---------------------------------------------------------------------------

def test_exact_query_reaches_api():
    captured_urls = []

    def _side(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ZERO_RESULTS_RESPONSE)

    query = '("Metformin") AND ("type 2 diabetes")'
    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter().search(_strategy(query=query))

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "Metformin" in decoded
    assert "type 2 diabetes" in decoded


def test_query_preserved_in_result():
    query = '("Metformin") AND ("type 2 diabetes")'
    with _patch_urlopen(_ZERO_RESULTS_RESPONSE):
        result = _adapter().search(_strategy(query=query))
    assert result.query == query


def test_query_not_rewritten():
    captured_urls = []

    def _side(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ZERO_RESULTS_RESPONSE)

    query = '("Aspirin") AND ("heart failure")'
    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter().search(_strategy(query=query))

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "Aspirin" in decoded
    assert "heart failure" in decoded


# ---------------------------------------------------------------------------
# 12. Max results bound
# ---------------------------------------------------------------------------

def test_default_max_results_is_100():
    assert _DEFAULT_MAX_RESULTS == 100


def test_max_results_sent_in_request():
    captured_urls = []

    def _side(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ZERO_RESULTS_RESPONSE)

    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter(max_results=25).search(_strategy())

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "pageSize=25" in decoded


def test_custom_max_results_stored():
    adapter = EuropePMCAdapter(max_results=50)
    assert adapter._max_results == 50


# ---------------------------------------------------------------------------
# 13. Timeout
# ---------------------------------------------------------------------------

def test_timeout_applied():
    used_timeouts = []

    def _side(req, timeout=None):
        used_timeouts.append(timeout)
        return _mock_response(_ZERO_RESULTS_RESPONSE)

    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter(timeout=20).search(_strategy())

    assert used_timeouts[0] == 20


# ---------------------------------------------------------------------------
# 14. HTTP errors become LiteratureSourceError
# ---------------------------------------------------------------------------

def test_http_error_raises_source_error():
    err = urllib.error.HTTPError(
        url="http://x", code=500, msg="Internal Server Error",
        hdrs=None, fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


def test_url_error_raises_source_error():
    err = urllib.error.URLError(reason="Name resolution failed")
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


def test_source_error_source_is_europe_pmc():
    err = urllib.error.HTTPError(
        url="http://x", code=503, msg="Service Unavailable",
        hdrs=None, fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(LiteratureSourceError) as exc_info:
            _adapter().search(_strategy())
    assert exc_info.value.source == ExternalSource.EUROPE_PMC


# ---------------------------------------------------------------------------
# 15. Malformed JSON raises LiteratureSourceError
# ---------------------------------------------------------------------------

def test_malformed_json_raises_source_error():
    with _patch_urlopen(_MALFORMED_JSON):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


def test_missing_result_list_raises_source_error():
    body = json.dumps({"unexpected": "structure"}).encode()
    with _patch_urlopen(body):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


# ---------------------------------------------------------------------------
# 16. Source contract
# ---------------------------------------------------------------------------

def test_europe_pmc_adapter_is_literature_source_adapter():
    assert issubclass(EuropePMCAdapter, LiteratureSourceAdapter)


def test_europe_pmc_adapter_has_search_method():
    assert callable(getattr(EuropePMCAdapter, "search", None))


def test_search_returns_literature_search_result():
    with _patch_urlopen(_make_response([_FULL_RESULT])):
        result = _adapter().search(_strategy())
    assert isinstance(result, LiteratureSearchResult)


# ---------------------------------------------------------------------------
# 17. No AI in source
# ---------------------------------------------------------------------------

def test_no_ai_imports_in_module():
    import inspect
    import adapters.europe_pmc as mod
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


# ---------------------------------------------------------------------------
# 18. No HTTP library other than stdlib
# ---------------------------------------------------------------------------

def test_no_external_http_libraries():
    import inspect
    import adapters.europe_pmc as mod
    source = inspect.getsource(mod)
    assert "import requests" not in source
    assert "import aiohttp" not in source
    assert "import httpx" not in source


# ---------------------------------------------------------------------------
# 19. No invention
# ---------------------------------------------------------------------------

def test_no_invented_doi():
    with _patch_urlopen(_make_response([_NO_DOI_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].doi is None


def test_no_invented_pmid():
    with _patch_urlopen(_make_response([_NO_PMID_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid is None


def test_no_invented_abstract():
    with _patch_urlopen(_make_response([_NO_ABSTRACT_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is None


def test_no_invented_pub_date():
    with _patch_urlopen(_make_response([_NO_PUBDATE_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date is None


def test_no_invented_authors():
    with _patch_urlopen(_make_response([_NO_AUTHORS_RESULT])):
        result = _adapter().search(_strategy())
    assert result.records[0].authors == []


# ---------------------------------------------------------------------------
# 20. Public import
# ---------------------------------------------------------------------------

def test_europe_pmc_adapter_importable_from_adapters():
    from adapters import EuropePMCAdapter
    assert EuropePMCAdapter is not None


def test_pubmed_adapter_still_importable():
    from adapters import PubMedAdapter
    assert PubMedAdapter is not None


# ---------------------------------------------------------------------------
# 21. Strategy not mutated
# ---------------------------------------------------------------------------

def test_strategy_not_mutated_by_search():
    strategy = _strategy(query='("Aspirin") AND ("stroke")')
    original_query = strategy.boolean_query
    with _patch_urlopen(_ZERO_RESULTS_RESPONSE):
        _adapter().search(strategy)
    assert strategy.boolean_query == original_query


# ---------------------------------------------------------------------------
# 22. User-Agent header present
# ---------------------------------------------------------------------------

def test_user_agent_sent():
    captured_headers = []

    def _side(req, timeout=None):
        captured_headers.append(req.get_header("User-agent"))
        return _mock_response(_ZERO_RESULTS_RESPONSE)

    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter().search(_strategy())

    assert captured_headers[0] is not None
    assert len(captured_headers[0]) > 0
