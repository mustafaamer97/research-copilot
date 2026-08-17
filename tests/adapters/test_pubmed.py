"""Tests for PubMedAdapter — all HTTP is mocked; no live network calls."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from adapters.pubmed import PubMedAdapter, _DEFAULT_MAX_RESULTS
from domain.framework import FrameworkType
from domain.literature import ExternalSource
from domain.literature_search import LiteratureSearchStrategy
from services.literature_source import LiteratureSearchResult, LiteratureSourceError

# ---------------------------------------------------------------------------
# XML / JSON fixtures
# ---------------------------------------------------------------------------

_ESEARCH_ONE = json.dumps({
    "esearchresult": {"idlist": ["12345678"]}
}).encode()

_ESEARCH_TWO = json.dumps({
    "esearchresult": {"idlist": ["12345678", "99887766"]}
}).encode()

_ESEARCH_ZERO = json.dumps({
    "esearchresult": {"idlist": []}
}).encode()

_ESEARCH_MALFORMED = b"not json at all {{{"

_EFETCH_FULL = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Effect of Metformin on Cardiovascular Mortality</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
            <Initials>J</Initials>
          </Author>
          <Author>
            <LastName>Jones</LastName>
            <ForeName>Kate</ForeName>
            <Initials>K</Initials>
          </Author>
        </AuthorList>
        <Journal>
          <Title>Journal of Medicine</Title>
          <JournalIssue>
            <PubDate><Year>2023</Year><Month>06</Month><Day>15</Day></PubDate>
          </JournalIssue>
        </Journal>
        <Abstract>
          <AbstractText>Background: This study examined metformin.</AbstractText>
        </Abstract>
        <ArticleDate>
          <Year>2023</Year><Month>06</Month><Day>15</Day>
        </ArticleDate>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1234/example.doi</ArticleId>
        <ArticleId IdType="pubmed">12345678</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

_EFETCH_NO_DOI = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>99887766</PMID>
      <Article>
        <ArticleTitle>Smoking and Lung Cancer Risk</ArticleTitle>
        <AuthorList/>
        <Journal>
          <Title>Epidemiology Today</Title>
          <JournalIssue>
            <PubDate><Year>2022</Year></PubDate>
          </JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">99887766</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

_EFETCH_NO_ABSTRACT = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>11111111</PMID>
      <Article>
        <ArticleTitle>A Study Without Abstract</ArticleTitle>
        <Journal>
          <Title>Brief Reports</Title>
          <JournalIssue><PubDate><Year>2021</Year></PubDate></JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">11111111</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

_EFETCH_NO_PUBDATE = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>22222222</PMID>
      <Article>
        <ArticleTitle>Article With No Publication Date</ArticleTitle>
        <Journal>
          <Title>Undated Journal</Title>
          <JournalIssue><PubDate></PubDate></JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">22222222</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

_EFETCH_NO_AUTHORS = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>33333333</PMID>
      <Article>
        <ArticleTitle>Consensus Statement</ArticleTitle>
        <AuthorList/>
        <Journal>
          <Title>Guidelines Journal</Title>
          <JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">33333333</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

_EFETCH_MALFORMED_XML = b"<this is not xml <<<"

_EFETCH_STRUCTURED_ABSTRACT = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>44444444</PMID>
      <Article>
        <ArticleTitle>Structured Abstract Article</ArticleTitle>
        <Journal>
          <Title>Clinical Research</Title>
          <JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue>
        </Journal>
        <Abstract>
          <AbstractText Label="BACKGROUND">Background text here.</AbstractText>
          <AbstractText Label="METHODS">Methods text here.</AbstractText>
          <AbstractText Label="RESULTS">Results text here.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">44444444</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strategy(query: str = '("Metformin") AND ("type 2 diabetes")') -> LiteratureSearchStrategy:
    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        population_terms=["Adults with type 2 diabetes"],
        intervention_terms=["Metformin"],
        comparator_terms=["Placebo"],
        outcome_terms=["Cardiovascular mortality"],
        boolean_query=query,
    )


def _adapter(**kwargs) -> PubMedAdapter:
    return PubMedAdapter(**kwargs)


def _mock_response(body: bytes, status: int = 200):
    resp = MagicMock()
    resp.read.return_value = body
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _patch_urlopen(responses: list[bytes]):
    """Patch urlopen to return successive mock responses."""
    calls = iter(responses)

    def _side_effect(req, timeout=None):
        return _mock_response(next(calls))

    return patch("urllib.request.urlopen", side_effect=_side_effect)


# ---------------------------------------------------------------------------
# 1. Successful single-result search
# ---------------------------------------------------------------------------

def test_successful_search_returns_result():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert isinstance(result, LiteratureSearchResult)


def test_successful_search_source_is_pubmed():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.source == ExternalSource.PUBMED


def test_successful_search_returns_one_record():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert len(result.records) == 1


def test_successful_search_retrieved_at_is_utc():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.retrieved_at.tzinfo is not None


# ---------------------------------------------------------------------------
# 2. Multiple PMIDs
# ---------------------------------------------------------------------------

def test_multiple_pmids_returns_multiple_records():
    combined_xml = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation><PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Article One</ArticleTitle>
        <Journal><Title>J One</Title>
          <JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
    <PubmedData><ArticleIdList>
      <ArticleId IdType="pubmed">12345678</ArticleId>
    </ArticleIdList></PubmedData>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation><PMID>99887766</PMID>
      <Article>
        <ArticleTitle>Article Two</ArticleTitle>
        <Journal><Title>J Two</Title>
          <JournalIssue><PubDate><Year>2022</Year></PubDate></JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
    <PubmedData><ArticleIdList>
      <ArticleId IdType="pubmed">99887766</ArticleId>
    </ArticleIdList></PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""
    with _patch_urlopen([_ESEARCH_TWO, combined_xml]):
        result = _adapter().search(_strategy())
    assert len(result.records) == 2


# ---------------------------------------------------------------------------
# 3. Zero results
# ---------------------------------------------------------------------------

def test_zero_results_returns_empty_records():
    with _patch_urlopen([_ESEARCH_ZERO]):
        result = _adapter().search(_strategy())
    assert result.records == []


def test_zero_results_is_not_an_error():
    with _patch_urlopen([_ESEARCH_ZERO]):
        result = _adapter().search(_strategy())
    assert result is not None


# ---------------------------------------------------------------------------
# 4. Malformed ESearch JSON raises LiteratureSourceError
# ---------------------------------------------------------------------------

def test_malformed_esearch_json_raises_source_error():
    with _patch_urlopen([_ESEARCH_MALFORMED]):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


# ---------------------------------------------------------------------------
# 5. HTTP failure raises LiteratureSourceError
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


# ---------------------------------------------------------------------------
# 6. Malformed EFetch XML raises LiteratureSourceError
# ---------------------------------------------------------------------------

def test_malformed_efetch_xml_raises_source_error():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_MALFORMED_XML]):
        with pytest.raises(LiteratureSourceError):
            _adapter().search(_strategy())


# ---------------------------------------------------------------------------
# 7. Record mapping — full record
# ---------------------------------------------------------------------------

def test_full_record_pmid():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid == "12345678"


def test_full_record_source_record_id_equals_pmid():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    rec = result.records[0]
    assert rec.source_record_id == rec.pmid


def test_full_record_source_is_pubmed():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.records[0].source == ExternalSource.PUBMED


def test_full_record_title():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.records[0].title == "Effect of Metformin on Cardiovascular Mortality"


def test_full_record_authors():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    authors = result.records[0].authors
    assert "Smith John" in authors
    assert "Jones Kate" in authors


def test_full_record_journal():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.records[0].journal == "Journal of Medicine"


def test_full_record_doi():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.records[0].doi == "10.1234/example.doi"


def test_full_record_abstract():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is not None
    assert "metformin" in result.records[0].abstract.lower()


def test_full_record_publication_date():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date == "2023-06-15"


def test_full_record_source_url():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.records[0].source_url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"


# ---------------------------------------------------------------------------
# 8. Missing DOI → None
# ---------------------------------------------------------------------------

def test_missing_doi_is_none():
    esearch = json.dumps({"esearchresult": {"idlist": ["99887766"]}}).encode()
    with _patch_urlopen([esearch, _EFETCH_NO_DOI]):
        result = _adapter().search(_strategy())
    assert result.records[0].doi is None


# ---------------------------------------------------------------------------
# 9. Missing abstract → None
# ---------------------------------------------------------------------------

def test_missing_abstract_is_none():
    esearch = json.dumps({"esearchresult": {"idlist": ["11111111"]}}).encode()
    with _patch_urlopen([esearch, _EFETCH_NO_ABSTRACT]):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is None


# ---------------------------------------------------------------------------
# 10. No authors → empty list
# ---------------------------------------------------------------------------

def test_no_authors_returns_empty_list():
    esearch = json.dumps({"esearchresult": {"idlist": ["33333333"]}}).encode()
    with _patch_urlopen([esearch, _EFETCH_NO_AUTHORS]):
        result = _adapter().search(_strategy())
    assert result.records[0].authors == []


# ---------------------------------------------------------------------------
# 11. Missing publication date → None
# ---------------------------------------------------------------------------

def test_missing_pub_date_is_none():
    esearch = json.dumps({"esearchresult": {"idlist": ["22222222"]}}).encode()
    with _patch_urlopen([esearch, _EFETCH_NO_PUBDATE]):
        result = _adapter().search(_strategy())
    assert result.records[0].publication_date is None


# ---------------------------------------------------------------------------
# 12. Structured abstract preserved
# ---------------------------------------------------------------------------

def test_structured_abstract_preserved():
    esearch = json.dumps({"esearchresult": {"idlist": ["44444444"]}}).encode()
    with _patch_urlopen([esearch, _EFETCH_STRUCTURED_ABSTRACT]):
        result = _adapter().search(_strategy())
    abstract = result.records[0].abstract
    assert abstract is not None
    assert "BACKGROUND" in abstract
    assert "METHODS" in abstract
    assert "RESULTS" in abstract


# ---------------------------------------------------------------------------
# 13. Query integrity — exact query reaches ESearch
# ---------------------------------------------------------------------------

def test_exact_query_reaches_esearch():
    captured_urls = []

    def _side_effect(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ESEARCH_ZERO)

    query = '("Metformin") AND ("type 2 diabetes")'
    with patch("urllib.request.urlopen", side_effect=_side_effect):
        _adapter().search(_strategy(query=query))

    assert len(captured_urls) >= 1
    from urllib.parse import unquote
    decoded = unquote(captured_urls[0])
    assert "Metformin" in decoded
    assert "type 2 diabetes" in decoded


def test_query_preserved_in_result():
    query = '("Metformin") AND ("type 2 diabetes")'
    with _patch_urlopen([_ESEARCH_ZERO]):
        result = _adapter().search(_strategy(query=query))
    assert result.query == query


# ---------------------------------------------------------------------------
# 14. Max results bound
# ---------------------------------------------------------------------------

def test_default_max_results_constant():
    assert _DEFAULT_MAX_RESULTS == 100


def test_max_results_sent_in_esearch_request():
    captured_urls = []

    def _side_effect(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ESEARCH_ZERO)

    with patch("urllib.request.urlopen", side_effect=_side_effect):
        _adapter(max_results=50).search(_strategy())

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "retmax=50" in decoded


def test_custom_max_results_applied():
    adapter = PubMedAdapter(max_results=10)
    assert adapter._max_results == 10


# ---------------------------------------------------------------------------
# 15. Timeout is set
# ---------------------------------------------------------------------------

def test_timeout_is_applied():
    used_timeouts = []

    def _side_effect(req, timeout=None):
        used_timeouts.append(timeout)
        return _mock_response(_ESEARCH_ZERO)

    with patch("urllib.request.urlopen", side_effect=_side_effect):
        _adapter(timeout=15).search(_strategy())

    assert used_timeouts[0] == 15


# ---------------------------------------------------------------------------
# 16. No live network calls during tests
# ---------------------------------------------------------------------------

def test_no_live_network_calls_possible():
    """Verify that without mocking, urlopen would be the only network path."""
    import inspect
    import adapters.pubmed as mod
    source = inspect.getsource(mod)
    assert "urllib.request.urlopen" in source
    assert "requests." not in source
    assert "aiohttp" not in source
    assert "httpx" not in source


# ---------------------------------------------------------------------------
# 17. LiteratureSourceError wraps HTTP errors
# ---------------------------------------------------------------------------

def test_source_error_source_is_pubmed():
    err = urllib.error.HTTPError(
        url="http://x", code=503, msg="Service Unavailable",
        hdrs=None, fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(LiteratureSourceError) as exc_info:
            _adapter().search(_strategy())
    assert exc_info.value.source == ExternalSource.PUBMED


def test_source_error_message_is_informative():
    err = urllib.error.URLError(reason="Network is unreachable")
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(LiteratureSourceError) as exc_info:
            _adapter().search(_strategy())
    assert len(exc_info.value.message) > 0


# ---------------------------------------------------------------------------
# 18. No invention
# ---------------------------------------------------------------------------

def test_no_invented_pmid():
    with _patch_urlopen([_ESEARCH_ONE, _EFETCH_FULL]):
        result = _adapter().search(_strategy())
    assert result.records[0].pmid == "12345678"


def test_no_invented_doi():
    esearch = json.dumps({"esearchresult": {"idlist": ["99887766"]}}).encode()
    with _patch_urlopen([esearch, _EFETCH_NO_DOI]):
        result = _adapter().search(_strategy())
    assert result.records[0].doi is None


def test_no_invented_abstract():
    esearch = json.dumps({"esearchresult": {"idlist": ["11111111"]}}).encode()
    with _patch_urlopen([esearch, _EFETCH_NO_ABSTRACT]):
        result = _adapter().search(_strategy())
    assert result.records[0].abstract is None


# ---------------------------------------------------------------------------
# 19. Adapter implements contract
# ---------------------------------------------------------------------------

def test_pubmed_adapter_is_literature_source_adapter():
    from services.literature_source import LiteratureSourceAdapter
    assert issubclass(PubMedAdapter, LiteratureSourceAdapter)


def test_pubmed_adapter_has_search_method():
    assert callable(getattr(PubMedAdapter, "search", None))


# ---------------------------------------------------------------------------
# 20. Public import
# ---------------------------------------------------------------------------

def test_pubmed_adapter_importable_from_adapters():
    from adapters import PubMedAdapter
    assert PubMedAdapter is not None


# ---------------------------------------------------------------------------
# 21. User-Agent header present
# ---------------------------------------------------------------------------

def test_user_agent_header_sent():
    captured_headers = []

    def _side_effect(req, timeout=None):
        captured_headers.append(req.get_header("User-agent"))
        return _mock_response(_ESEARCH_ZERO)

    with patch("urllib.request.urlopen", side_effect=_side_effect):
        _adapter().search(_strategy())

    assert captured_headers[0] is not None
    assert len(captured_headers[0]) > 0


# ---------------------------------------------------------------------------
# 22. Email configurable, not hard-coded
# ---------------------------------------------------------------------------

def test_email_not_hard_coded_in_module():
    import inspect
    import adapters.pubmed as mod
    source = inspect.getsource(mod)
    assert "@gmail.com" not in source
    assert "@yahoo.com" not in source
    assert "@hotmail.com" not in source


def test_email_sent_when_configured():
    captured_urls = []

    def _side_effect(req, timeout=None):
        captured_urls.append(req.full_url)
        return _mock_response(_ESEARCH_ZERO)

    with patch("urllib.request.urlopen", side_effect=_side_effect):
        PubMedAdapter(email="researcher@university.edu").search(_strategy())

    decoded = urllib.parse.unquote(captured_urls[0])
    assert "researcher@university.edu" in decoded
