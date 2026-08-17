"""Tests for OpenAlexAdapter — all HTTP is mocked; no live network calls."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from adapters.openalex import OpenAlexAdapter, _DEFAULT_MAX_RESULTS
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

_FULL_WORK = {
    "id": "https://openalex.org/W2741809807",
    "title": "Effect of Metformin on Cardiovascular Mortality in Type 2 Diabetes",
    "doi": "https://doi.org/10.1234/metformin.study",
    "ids": {
        "openalex": "https://openalex.org/W2741809807",
        "pmid": "https://pubmed.ncbi.nlm.nih.gov/29800000",
    },
    "publication_date": "2023-05-14",
    "primary_location": {
        "source": {"display_name": "New England Journal of Medicine"}
    },
    "authorships": [
        {"author": {"display_name": "Jane Smith"}},
        {"author": {"display_name": "Alex Brown"}},
    ],
    "abstract_inverted_index": {
        "Metformin": [0],
        "was": [1],
        "associated": [2],
        "with": [3],
        "cardiovascular": [4],
        "outcomes": [5],
    },
}

_NO_DOI_WORK = {
    "id": "https://openalex.org/W1111111111",
    "title": "Smoking and Lung Cancer: A Prospective Study",
    "ids": {"openalex": "https://openalex.org/W1111111111"},
    "publication_date": "2022-03-01",
    "primary_location": {
        "source": {"display_name": "Thorax"}
    },
    "authorships": [{"author": {"display_name": "Carlos Rivera"}}],
}

_NO_PMID_WORK = {
    "id": "https://openalex.org/W2222222222",
    "title": "Machine Learning in Clinical Trials",
    "doi": "https://doi.org/10.5678/ml.trials",
    "ids": {"openalex": "https://openalex.org/W2222222222"},
    "publication_date": "2021-09-20",
    "primary_location": {"source": {"display_name": "Nature Medicine"}},
    "authorships": [{"author": {"display_name": "Sara Lee"}}],
}

_NO_ABSTRACT_WORK = {
    "id": "https://openalex.org/W3333333333",
    "title": "Brief Correspondence Without Abstract",
    "doi": "https://doi.org/10.9999/brief",
    "ids": {
        "openalex": "https://openalex.org/W3333333333",
        "pmid": "https://pubmed.ncbi.nlm.nih.gov/31000000",
    },
    "publication_date": "2020-11-05",
    "primary_location": {"source": {"display_name": "Lancet"}},
    "authorships": [{"author": {"display_name": "Tom Hardy"}}],
}

_NO_AUTHORS_WORK = {
    "id": "https://openalex.org/W4444444444",
    "title": "Consensus Guidelines on Diabetes Management",
    "doi": "https://doi.org/10.1111/guidelines",
    "ids": {"openalex": "https://openalex.org/W4444444444"},
    "publication_date": "2019-06-30",
    "primary_location": {"source": {"display_name": "Diabetologia"}},
    "authorships": [],
}

_NO_JOURNAL_WORK = {
    "id": "https://openalex.org/W5555555555",
    "title": "Preprint Without Journal",
    "doi": "https://doi.org/10.1101/2023.preprint",
    "ids": {"openalex": "https://openalex.org/W5555555555"},
    "publication_date": "2023-01-10",
    "primary_location": None,
    "authorships": [{"author": {"display_name": "Kim Park"}}],
}

_NO_PUBDATE_WORK = {
    "id": "https://openalex.org/W6666666666",
    "title": "Article With No Publication Date",
    "doi": "https://doi.org/10.2222/noddate",
    "ids": {"openalex": "https://openalex.org/W6666666666"},
    "primary_location": {"source": {"display_name": "Review Journal"}},
    "authorships": [{"author": {"display_name": "Anna White"}}],
}

_INVERTED_INDEX_MULTIPOS = {
    "id": "https://openalex.org/W7777777777",
    "title": "Multi-Position Abstract Test",
    "ids": {"openalex": "https://openalex.org/W7777777777"},
    "publication_date": "2023-08-01",
    "primary_location": {"source": {"display_name": "Test Journal"}},
    "authorships": [],
    "abstract_inverted_index": {
        "The": [0, 6],
        "quick": [1],
        "brown": [2],
        "fox": [3],
        "jumps": [4],
        "over": [5],
        "lazy": [7],
        "dog": [8],
    },
}


def _make_response(results: list[dict]) -> bytes:
    return json.dumps({"results": results, "meta": {"count": len(results)}}).encode()


_ZERO_RESULTS = _make_response([])
_MALFORMED_JSON = b"not json {{{"
_MISSING_RESULTS_KEY = json.dumps({"meta": {"count": 0}}).encode()


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


def _adapter(**kwargs) -> OpenAlexAdapter:
    return OpenAlexAdapter(**kwargs)


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


# ---------------------------------------------------------------------------
# 1. Successful search
# ---------------------------------------------------------------------------

def test_successful_search_returns_result():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert isinstance(result, LiteratureSearchResult)


def test_successful_search_source_is_openalex():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert result.source == ExternalSource.OPENALEX


def test_successful_search_returns_one_record():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert len(result.records) == 1


def test_result_retrieved_at_is_utc():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert result.retrieved_at.tzinfo is not None


# ---------------------------------------------------------------------------
# 2. Full record mapping
# ---------------------------------------------------------------------------

def test_full_record_source_record_id():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert "W2741809807" in result.records[0].source_record_id


def test_full_record_source_is_openalex():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].source == ExternalSource.OPENALEX


def test_full_record_title():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert (
        result.records[0].title
        == "Effect of Metformin on Cardiovascular Mortality in Type 2 Diabetes"
    )


def test_full_record_authors():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    authors = result.records[0].authors
    assert any("Smith" in a for a in authors)
    assert any("Brown" in a for a in authors)


def test_full_record_journal():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].journal == "New England Journal of Medicine"


def test_full_record_publication_date():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date == "2023-05-14"


def test_full_record_doi():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].doi == "10.1234/metformin.study"


def test_full_record_pmid():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid == "29800000"


def test_full_record_source_url_set():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].source_url is not None
    assert len(result.records[0].source_url) > 0


# ---------------------------------------------------------------------------
# 3. Abstract reconstruction from inverted index
# ---------------------------------------------------------------------------

def test_abstract_reconstructed_from_inverted_index():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    abstract = result.records[0].abstract
    assert abstract is not None
    assert abstract == "Metformin was associated with cardiovascular outcomes"


def test_abstract_multiposition_reconstruction():
    with _patch_urlopen(_make_response([_INVERTED_INDEX_MULTIPOS])):
        result = _adapter().search(_strategy())
    abstract = result.records[0].abstract
    assert abstract is not None
    assert abstract == "The quick brown fox jumps over The lazy dog"


def test_abstract_words_not_modified():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    abstract = result.records[0].abstract
    assert "Metformin" in abstract
    assert "cardiovascular" in abstract


def test_missing_abstract_is_none():
    with _patch_urlopen(_make_response([_NO_ABSTRACT_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is None


# ---------------------------------------------------------------------------
# 4. Missing DOI → None
# ---------------------------------------------------------------------------

def test_missing_doi_is_none():
    with _patch_urlopen(_make_response([_NO_DOI_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].doi is None


# ---------------------------------------------------------------------------
# 5. Missing PMID → None
# ---------------------------------------------------------------------------

def test_missing_pmid_is_none():
    with _patch_urlopen(_make_response([_NO_PMID_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid is None


# ---------------------------------------------------------------------------
# 6. Missing authors → empty list
# ---------------------------------------------------------------------------

def test_missing_authors_returns_empty_list():
    with _patch_urlopen(_make_response([_NO_AUTHORS_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].authors == []


# ---------------------------------------------------------------------------
# 7. Missing journal → None
# ---------------------------------------------------------------------------

def test_missing_journal_is_none():
    with _patch_urlopen(_make_response([_NO_JOURNAL_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].journal is None


# ---------------------------------------------------------------------------
# 8. Missing publication date → None
# ---------------------------------------------------------------------------

def test_missing_pub_date_is_none():
    with _patch_urlopen(_make_response([_NO_PUBDATE_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date is None


# ---------------------------------------------------------------------------
# 9. Multiple records
# ---------------------------------------------------------------------------

def test_multiple_records_returned():
    with _patch_urlopen(_make_response([_FULL_WORK, _NO_DOI_WORK])):
        result = _adapter().search(_strategy())
    assert len(result.records) == 2


def test_multiple_records_are_literature_record_instances():
    with _patch_urlopen(_make_response([_FULL_WORK, _NO_DOI_WORK])):
        result = _adapter().search(_strategy())
    for rec in result.records:
        assert isinstance(rec, LiteratureRecord)


# ---------------------------------------------------------------------------
# 10. Zero results
# ---------------------------------------------------------------------------

def test_zero_results_returns_empty_records():
    with _patch_urlopen(_ZERO_RESULTS):
        result = _adapter().search(_strategy())
    assert result.records == []


def test_zero_results_is_not_an_error():
    with _patch_urlopen(_ZERO_RESULTS):
        result = _adapter().search(_strategy())
    assert result is not None


# ---------------------------------------------------------------------------
# 11. Query integrity
# ---------------------------------------------------------------------------

def test_exact_query_reaches_api():
    captured_urls = []

    def _side(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ZERO_RESULTS)

    query = '("Metformin") AND ("type 2 diabetes")'
    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter().search(_strategy(query=query))

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "Metformin" in decoded
    assert "type 2 diabetes" in decoded


def test_query_preserved_in_result():
    query = '("Aspirin") AND ("stroke prevention")'
    with _patch_urlopen(_ZERO_RESULTS):
        result = _adapter().search(_strategy(query=query))
    assert result.query == query


def test_query_not_rewritten():
    captured_urls = []

    def _side(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ZERO_RESULTS)

    query = '("Insulin") AND ("glycaemic control")'
    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter().search(_strategy(query=query))

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "Insulin" in decoded
    assert "glycaemic control" in decoded


# ---------------------------------------------------------------------------
# 12. Max results bound
# ---------------------------------------------------------------------------

def test_default_max_results_is_100():
    assert _DEFAULT_MAX_RESULTS == 100


def test_max_results_sent_in_request():
    captured_urls = []

    def _side(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ZERO_RESULTS)

    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter(max_results=25).search(_strategy())

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "per_page=25" in decoded


def test_custom_max_results_stored():
    adapter = OpenAlexAdapter(max_results=50)
    assert adapter._max_results == 50


# ---------------------------------------------------------------------------
# 13. Timeout
# ---------------------------------------------------------------------------

def test_timeout_applied():
    used_timeouts = []

    def _side(req, timeout=None):
        used_timeouts.append(timeout)
        return _mock_response(_ZERO_RESULTS)

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


def test_source_error_source_is_openalex():
    err = urllib.error.HTTPError(
        url="http://x", code=503, msg="Service Unavailable",
        hdrs=None, fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(LiteratureSourceError) as exc_info:
            _adapter().search(_strategy())
    assert exc_info.value.source == ExternalSource.OPENALEX


# ---------------------------------------------------------------------------
# 15. Malformed JSON raises LiteratureSourceError
# ---------------------------------------------------------------------------

def test_malformed_json_raises_source_error():
    with _patch_urlopen(_MALFORMED_JSON):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


def test_missing_results_key_raises_source_error():
    with _patch_urlopen(_MISSING_RESULTS_KEY):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


# ---------------------------------------------------------------------------
# 16. Source contract
# ---------------------------------------------------------------------------

def test_openalex_adapter_is_literature_source_adapter():
    assert issubclass(OpenAlexAdapter, LiteratureSourceAdapter)


def test_openalex_adapter_has_search_method():
    assert callable(getattr(OpenAlexAdapter, "search", None))


def test_search_returns_literature_search_result():
    with _patch_urlopen(_make_response([_FULL_WORK])):
        result = _adapter().search(_strategy())
    assert isinstance(result, LiteratureSearchResult)


# ---------------------------------------------------------------------------
# 17. No AI
# ---------------------------------------------------------------------------

def test_no_ai_imports_in_module():
    import inspect
    import adapters.openalex as mod
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


# ---------------------------------------------------------------------------
# 18. No external HTTP libraries
# ---------------------------------------------------------------------------

def test_no_external_http_libraries():
    import inspect
    import adapters.openalex as mod
    source = inspect.getsource(mod)
    assert "import requests" not in source
    assert "import aiohttp" not in source
    assert "import httpx" not in source


# ---------------------------------------------------------------------------
# 19. No invention
# ---------------------------------------------------------------------------

def test_no_invented_doi():
    with _patch_urlopen(_make_response([_NO_DOI_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].doi is None


def test_no_invented_pmid():
    with _patch_urlopen(_make_response([_NO_PMID_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid is None


def test_no_invented_abstract():
    with _patch_urlopen(_make_response([_NO_ABSTRACT_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is None


def test_no_invented_pub_date():
    with _patch_urlopen(_make_response([_NO_PUBDATE_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date is None


def test_no_invented_authors():
    with _patch_urlopen(_make_response([_NO_AUTHORS_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].authors == []


def test_no_invented_journal():
    with _patch_urlopen(_make_response([_NO_JOURNAL_WORK])):
        result = _adapter().search(_strategy())
    assert result.records[0].journal is None


# ---------------------------------------------------------------------------
# 20. Strategy not mutated
# ---------------------------------------------------------------------------

def test_strategy_not_mutated():
    strategy = _strategy()
    original_query = strategy.boolean_query
    with _patch_urlopen(_ZERO_RESULTS):
        _adapter().search(strategy)
    assert strategy.boolean_query == original_query


# ---------------------------------------------------------------------------
# 21. User-Agent header
# ---------------------------------------------------------------------------

def test_user_agent_sent():
    captured_headers = []

    def _side(req, timeout=None):
        captured_headers.append(req.get_header("User-agent"))
        return _mock_response(_ZERO_RESULTS)

    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter().search(_strategy())

    assert captured_headers[0] is not None
    assert len(captured_headers[0]) > 0


# ---------------------------------------------------------------------------
# 22. Email / mailto configurable
# ---------------------------------------------------------------------------

def test_email_not_hard_coded():
    import inspect
    import adapters.openalex as mod
    source = inspect.getsource(mod)
    assert "@gmail.com" not in source
    assert "@yahoo.com" not in source


def test_email_sent_when_configured():
    captured_urls = []

    def _side(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ZERO_RESULTS)

    with patch("urllib.request.urlopen", side_effect=_side):
        OpenAlexAdapter(email="researcher@university.edu").search(_strategy())

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "researcher@university.edu" in decoded


# ---------------------------------------------------------------------------
# 23. Public import
# ---------------------------------------------------------------------------

def test_openalex_adapter_importable_from_adapters():
    from adapters import OpenAlexAdapter
    assert OpenAlexAdapter is not None


def test_all_adapters_still_importable():
    from adapters import EuropePMCAdapter, OpenAlexAdapter, PubMedAdapter
    assert PubMedAdapter is not None
    assert EuropePMCAdapter is not None
    assert OpenAlexAdapter is not None
