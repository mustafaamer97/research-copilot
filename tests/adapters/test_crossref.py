"""Tests for CrossrefAdapter — all HTTP is mocked; no live network calls."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from adapters.crossref import CrossrefAdapter, _DEFAULT_MAX_RESULTS, _strip_markup
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

_FULL_ITEM = {
    "DOI": "10.1234/metformin.study",
    "title": ["Effect of Metformin on Cardiovascular Outcomes in Type 2 Diabetes"],
    "author": [
        {"given": "Jane", "family": "Smith"},
        {"given": "Alex", "family": "Brown"},
    ],
    "container-title": ["New England Journal of Medicine"],
    "published-print": {"date-parts": [[2023, 5, 14]]},
    "abstract": (
        "<jats:p>Metformin was associated with reduced cardiovascular mortality "
        "in patients with type 2 diabetes.</jats:p>"
    ),
    "URL": "https://doi.org/10.1234/metformin.study",
}

_NO_DOI_ITEM = {
    "title": ["Smoking and Lung Cancer: A Cohort Study"],
    "author": [{"given": "Carlos", "family": "Rivera"}],
    "container-title": ["Thorax"],
    "published-print": {"date-parts": [[2022, 3, 1]]},
    "URL": "https://api.crossref.org/works/fallback-id-001",
}

_NO_ABSTRACT_ITEM = {
    "DOI": "10.5555/no.abstract",
    "title": ["Brief Correspondence"],
    "author": [{"given": "Tom", "family": "Hardy"}],
    "container-title": ["Lancet"],
    "published-print": {"date-parts": [[2020, 11, 5]]},
    "URL": "https://doi.org/10.5555/no.abstract",
}

_NO_AUTHORS_ITEM = {
    "DOI": "10.6666/consensus.guidelines",
    "title": ["Consensus Guidelines on Diabetes"],
    "author": [],
    "container-title": ["Diabetologia"],
    "published-print": {"date-parts": [[2019, 6, 30]]},
    "URL": "https://doi.org/10.6666/consensus.guidelines",
}

_NO_JOURNAL_ITEM = {
    "DOI": "10.7777/preprint.study",
    "title": ["Preprint Without Journal"],
    "author": [{"given": "Kim", "family": "Park"}],
    "published-print": {"date-parts": [[2023, 1, 10]]},
    "URL": "https://doi.org/10.7777/preprint.study",
}

_NO_PUBDATE_ITEM = {
    "DOI": "10.8888/noddate.study",
    "title": ["Article With No Publication Date"],
    "author": [{"given": "Anna", "family": "White"}],
    "container-title": ["Review Journal"],
    "URL": "https://doi.org/10.8888/noddate.study",
}

_JATS_ABSTRACT_ITEM = {
    "DOI": "10.9999/jats.abstract",
    "title": ["Structured Abstract Article"],
    "author": [{"given": "Paul", "family": "Jones"}],
    "container-title": ["Clinical Research"],
    "published-print": {"date-parts": [[2023, 8, 1]]},
    "abstract": (
        "<jats:abstract>"
        "<jats:title>Background</jats:title>"
        "<jats:p>Metformin was studied in T2DM.</jats:p>"
        "<jats:title>Methods</jats:title>"
        "<jats:p>A randomised controlled trial was conducted.</jats:p>"
        "</jats:abstract>"
    ),
    "URL": "https://doi.org/10.9999/jats.abstract",
}

_ONLINE_DATE_ITEM = {
    "DOI": "10.1111/online.date",
    "title": ["Online Date Article"],
    "author": [{"given": "Mary", "family": "Green"}],
    "container-title": ["BMJ"],
    "published-online": {"date-parts": [[2022, 7]]},
    "URL": "https://doi.org/10.1111/online.date",
}

_AUTHOR_NAME_FIELD_ITEM = {
    "DOI": "10.2222/collective.author",
    "title": ["Collective Author Study"],
    "author": [{"name": "International Diabetes Federation"}],
    "container-title": ["Diabetes Care"],
    "published-print": {"date-parts": [[2021, 4, 15]]},
    "URL": "https://doi.org/10.2222/collective.author",
}


def _make_response(items: list[dict]) -> bytes:
    return json.dumps({
        "status": "ok",
        "message": {
            "total-results": len(items),
            "items": items,
        },
    }).encode()


_ZERO_RESULTS = _make_response([])
_MALFORMED_JSON = b"not json {{{"
_MISSING_MESSAGE = json.dumps({"status": "ok"}).encode()
_MISSING_ITEMS = json.dumps({"status": "ok", "message": {"total-results": 0}}).encode()


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


def _adapter(**kwargs) -> CrossrefAdapter:
    return CrossrefAdapter(**kwargs)


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
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert isinstance(result, LiteratureSearchResult)


def test_successful_search_source_is_crossref():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.source == ExternalSource.CROSSREF


def test_successful_search_returns_one_record():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert len(result.records) == 1


def test_result_retrieved_at_is_utc():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.retrieved_at.tzinfo is not None


# ---------------------------------------------------------------------------
# 2. Full record mapping
# ---------------------------------------------------------------------------

def test_full_record_doi():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].doi == "10.1234/metformin.study"


def test_full_record_source_record_id_is_doi():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].source_record_id == "10.1234/metformin.study"


def test_full_record_source_is_crossref():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].source == ExternalSource.CROSSREF


def test_full_record_title():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert (
        result.records[0].title
        == "Effect of Metformin on Cardiovascular Outcomes in Type 2 Diabetes"
    )


def test_full_record_authors():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    authors = result.records[0].authors
    assert any("Smith" in a for a in authors)
    assert any("Brown" in a for a in authors)


def test_full_record_journal():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].journal == "New England Journal of Medicine"


def test_full_record_publication_date():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date == "2023-5-14"


def test_full_record_abstract_markup_stripped():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    abstract = result.records[0].abstract
    assert abstract is not None
    assert "<jats:p>" not in abstract
    assert "Metformin" in abstract
    assert "cardiovascular mortality" in abstract


def test_full_record_source_url_is_doi_url():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].source_url == "https://doi.org/10.1234/metformin.study"


def test_full_record_pmid_is_none():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid is None


# ---------------------------------------------------------------------------
# 3. JATS abstract stripped deterministically
# ---------------------------------------------------------------------------

def test_jats_abstract_stripped():
    with _patch_urlopen(_make_response([_JATS_ABSTRACT_ITEM])):
        result = _adapter().search(_strategy())
    abstract = result.records[0].abstract
    assert abstract is not None
    assert "<jats:" not in abstract
    assert "Background" in abstract
    assert "Metformin" in abstract
    assert "Methods" in abstract


def test_strip_markup_helper_deterministic():
    text = "<jats:title>Background</jats:title><jats:p>Content here.</jats:p>"
    result = _strip_markup(text)
    assert result == "BackgroundContent here."
    assert "<" not in result


def test_strip_markup_no_ai_called():
    # structural — no external calls
    result = _strip_markup("<p>Hello world</p>")
    assert result == "Hello world"


# ---------------------------------------------------------------------------
# 4. Missing DOI — source_record_id falls back to URL
# ---------------------------------------------------------------------------

def test_no_doi_source_record_id_uses_url():
    with _patch_urlopen(_make_response([_NO_DOI_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].doi is None
    assert "crossref.org" in result.records[0].source_record_id


# ---------------------------------------------------------------------------
# 5. Missing abstract → None
# ---------------------------------------------------------------------------

def test_missing_abstract_is_none():
    with _patch_urlopen(_make_response([_NO_ABSTRACT_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is None


# ---------------------------------------------------------------------------
# 6. Missing authors → empty list
# ---------------------------------------------------------------------------

def test_missing_authors_returns_empty_list():
    with _patch_urlopen(_make_response([_NO_AUTHORS_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].authors == []


# ---------------------------------------------------------------------------
# 7. Missing journal → None
# ---------------------------------------------------------------------------

def test_missing_journal_is_none():
    with _patch_urlopen(_make_response([_NO_JOURNAL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].journal is None


# ---------------------------------------------------------------------------
# 8. Missing publication date → None
# ---------------------------------------------------------------------------

def test_missing_pub_date_is_none():
    with _patch_urlopen(_make_response([_NO_PUBDATE_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date is None


# ---------------------------------------------------------------------------
# 9. Published-online date used as fallback
# ---------------------------------------------------------------------------

def test_online_date_used_as_fallback():
    with _patch_urlopen(_make_response([_ONLINE_DATE_ITEM])):
        result = _adapter().search(_strategy())
    pub_date = result.records[0].publication_date
    assert pub_date is not None
    assert "2022" in pub_date
    assert "7" in pub_date


# ---------------------------------------------------------------------------
# 10. Author with 'name' field (collective)
# ---------------------------------------------------------------------------

def test_collective_author_name_preserved():
    with _patch_urlopen(_make_response([_AUTHOR_NAME_FIELD_ITEM])):
        result = _adapter().search(_strategy())
    authors = result.records[0].authors
    assert any("International Diabetes Federation" in a for a in authors)


# ---------------------------------------------------------------------------
# 11. Multiple records
# ---------------------------------------------------------------------------

def test_multiple_records_returned():
    with _patch_urlopen(_make_response([_FULL_ITEM, _NO_ABSTRACT_ITEM])):
        result = _adapter().search(_strategy())
    assert len(result.records) == 2


def test_multiple_records_are_literature_record_instances():
    with _patch_urlopen(_make_response([_FULL_ITEM, _NO_ABSTRACT_ITEM])):
        result = _adapter().search(_strategy())
    for rec in result.records:
        assert isinstance(rec, LiteratureRecord)


# ---------------------------------------------------------------------------
# 12. Zero results
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
# 13. Query integrity
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
    query = '("Aspirin") AND ("stroke")'
    with _patch_urlopen(_ZERO_RESULTS):
        result = _adapter().search(_strategy(query=query))
    assert result.query == query


def test_query_not_rewritten():
    captured_urls = []

    def _side(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ZERO_RESULTS)

    query = '("Insulin glargine") AND ("glycaemic control")'
    with patch("urllib.request.urlopen", side_effect=_side):
        _adapter().search(_strategy(query=query))

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "Insulin glargine" in decoded


# ---------------------------------------------------------------------------
# 14. Max results bound
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
    assert "rows=25" in decoded


def test_custom_max_results_stored():
    adapter = CrossrefAdapter(max_results=50)
    assert adapter._max_results == 50


# ---------------------------------------------------------------------------
# 15. Timeout
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
# 16. HTTP errors
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


def test_source_error_source_is_crossref():
    err = urllib.error.HTTPError(
        url="http://x", code=503, msg="Service Unavailable",
        hdrs=None, fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(LiteratureSourceError) as exc_info:
            _adapter().search(_strategy())
    assert exc_info.value.source == ExternalSource.CROSSREF


# ---------------------------------------------------------------------------
# 17. Malformed JSON
# ---------------------------------------------------------------------------

def test_malformed_json_raises_source_error():
    with _patch_urlopen(_MALFORMED_JSON):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


def test_missing_message_raises_source_error():
    with _patch_urlopen(_MISSING_MESSAGE):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


def test_missing_items_raises_source_error():
    with _patch_urlopen(_MISSING_ITEMS):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


# ---------------------------------------------------------------------------
# 18. Source contract
# ---------------------------------------------------------------------------

def test_crossref_adapter_is_literature_source_adapter():
    assert issubclass(CrossrefAdapter, LiteratureSourceAdapter)


def test_crossref_adapter_has_search_method():
    assert callable(getattr(CrossrefAdapter, "search", None))


def test_search_returns_literature_search_result():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert isinstance(result, LiteratureSearchResult)


# ---------------------------------------------------------------------------
# 19. No AI
# ---------------------------------------------------------------------------

def test_no_ai_imports_in_module():
    import inspect
    import adapters.crossref as mod
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


# ---------------------------------------------------------------------------
# 20. No external HTTP libraries
# ---------------------------------------------------------------------------

def test_no_external_http_libraries():
    import inspect
    import adapters.crossref as mod
    source = inspect.getsource(mod)
    assert "import requests" not in source
    assert "import aiohttp" not in source
    assert "import httpx" not in source


# ---------------------------------------------------------------------------
# 21. No invention
# ---------------------------------------------------------------------------

def test_no_invented_doi():
    with _patch_urlopen(_make_response([_NO_DOI_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].doi is None


def test_no_invented_abstract():
    with _patch_urlopen(_make_response([_NO_ABSTRACT_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is None


def test_no_invented_pub_date():
    with _patch_urlopen(_make_response([_NO_PUBDATE_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date is None


def test_no_invented_authors():
    with _patch_urlopen(_make_response([_NO_AUTHORS_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].authors == []


def test_no_invented_journal():
    with _patch_urlopen(_make_response([_NO_JOURNAL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].journal is None


def test_pmid_always_none_crossref():
    with _patch_urlopen(_make_response([_FULL_ITEM])):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid is None


# ---------------------------------------------------------------------------
# 22. Strategy not mutated
# ---------------------------------------------------------------------------

def test_strategy_not_mutated():
    strategy = _strategy()
    original_query = strategy.boolean_query
    with _patch_urlopen(_ZERO_RESULTS):
        _adapter().search(strategy)
    assert strategy.boolean_query == original_query


# ---------------------------------------------------------------------------
# 23. User-Agent header
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
# 24. Mailto configurable
# ---------------------------------------------------------------------------

def test_mailto_not_hard_coded():
    import inspect
    import adapters.crossref as mod
    source = inspect.getsource(mod)
    assert "@gmail.com" not in source
    assert "@yahoo.com" not in source


def test_mailto_sent_when_configured():
    captured_urls = []

    def _side(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ZERO_RESULTS)

    with patch("urllib.request.urlopen", side_effect=_side):
        CrossrefAdapter(mailto="researcher@university.edu").search(_strategy())

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "researcher@university.edu" in decoded


# ---------------------------------------------------------------------------
# 25. Public import
# ---------------------------------------------------------------------------

def test_crossref_adapter_importable_from_adapters():
    from adapters import CrossrefAdapter
    assert CrossrefAdapter is not None


def test_all_adapters_still_importable():
    from adapters import CrossrefAdapter, EuropePMCAdapter, OpenAlexAdapter, PubMedAdapter
    assert PubMedAdapter is not None
    assert EuropePMCAdapter is not None
    assert OpenAlexAdapter is not None
    assert CrossrefAdapter is not None
