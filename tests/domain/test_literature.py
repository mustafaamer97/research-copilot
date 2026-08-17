"""Tests for literature domain contracts."""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from domain.literature import ExternalSource, LiteratureRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _valid_record(**kwargs) -> LiteratureRecord:
    defaults = dict(
        title="Effect of Drug A on Mortality in Adults",
        authors=["Smith J", "Jones K"],
        journal="Journal of Medicine",
        publication_date="2023-06-15",
        abstract="Background: ...",
        doi="10.1234/example.doi",
        pmid="12345678",
        source=ExternalSource.PUBMED,
        source_record_id="PMC12345678",
        source_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        retrieved_at=_utc_now(),
    )
    defaults.update(kwargs)
    return LiteratureRecord(**defaults)


# ---------------------------------------------------------------------------
# 1. Valid record creation
# ---------------------------------------------------------------------------

def test_valid_literature_record_can_be_created():
    record = _valid_record()
    assert record is not None
    assert record.title == "Effect of Drug A on Mortality in Adults"


def test_record_has_auto_generated_id():
    record = _valid_record()
    assert record.id is not None


def test_two_records_have_different_ids():
    r1 = _valid_record()
    r2 = _valid_record()
    assert r1.id != r2.id


# ---------------------------------------------------------------------------
# 2. All four ExternalSource values accepted
# ---------------------------------------------------------------------------

def test_pubmed_source_accepted():
    record = _valid_record(source=ExternalSource.PUBMED)
    assert record.source == ExternalSource.PUBMED


def test_europe_pmc_source_accepted():
    record = _valid_record(source=ExternalSource.EUROPE_PMC)
    assert record.source == ExternalSource.EUROPE_PMC


def test_openalex_source_accepted():
    record = _valid_record(source=ExternalSource.OPENALEX)
    assert record.source == ExternalSource.OPENALEX


def test_crossref_source_accepted():
    record = _valid_record(source=ExternalSource.CROSSREF)
    assert record.source == ExternalSource.CROSSREF


def test_exactly_four_external_sources():
    assert len(ExternalSource) == 4


def test_external_source_values():
    values = {s.value for s in ExternalSource}
    assert values == {"PUBMED", "EUROPE_PMC", "OPENALEX", "CROSSREF"}


# ---------------------------------------------------------------------------
# 3. Missing source is rejected
# ---------------------------------------------------------------------------

def test_missing_source_is_rejected():
    with pytest.raises(Exception):
        LiteratureRecord(
            title="A Title",
            source_record_id="ABC123",
            retrieved_at=_utc_now(),
        )


# ---------------------------------------------------------------------------
# 4. Missing source_record_id is rejected
# ---------------------------------------------------------------------------

def test_missing_source_record_id_is_rejected():
    with pytest.raises(Exception):
        LiteratureRecord(
            title="A Title",
            source=ExternalSource.PUBMED,
            retrieved_at=_utc_now(),
        )


# ---------------------------------------------------------------------------
# 5. Empty source_record_id is rejected
# ---------------------------------------------------------------------------

def test_empty_source_record_id_is_rejected():
    with pytest.raises(Exception):
        _valid_record(source_record_id="")


def test_whitespace_source_record_id_is_rejected():
    with pytest.raises(Exception):
        _valid_record(source_record_id="   ")


# ---------------------------------------------------------------------------
# 6. External IDs are preserved exactly
# ---------------------------------------------------------------------------

def test_doi_preserved_exactly():
    record = _valid_record(doi="10.1234/my.exact.doi")
    assert record.doi == "10.1234/my.exact.doi"


def test_pmid_preserved_exactly():
    record = _valid_record(pmid="99887766")
    assert record.pmid == "99887766"


def test_source_record_id_preserved_exactly():
    record = _valid_record(source_record_id="PMC-XYZ-9988")
    assert record.source_record_id == "PMC-XYZ-9988"


# ---------------------------------------------------------------------------
# 7. Optional DOI allowed
# ---------------------------------------------------------------------------

def test_none_doi_is_allowed():
    record = _valid_record(doi=None)
    assert record.doi is None


# ---------------------------------------------------------------------------
# 8. Optional PMID allowed
# ---------------------------------------------------------------------------

def test_none_pmid_is_allowed():
    record = _valid_record(pmid=None)
    assert record.pmid is None


# ---------------------------------------------------------------------------
# 9. Optional publication_date allowed
# ---------------------------------------------------------------------------

def test_none_publication_date_is_allowed():
    record = _valid_record(publication_date=None)
    assert record.publication_date is None


def test_no_invented_publication_date():
    record = _valid_record(publication_date=None)
    assert record.publication_date is None


# ---------------------------------------------------------------------------
# 10. Optional abstract allowed
# ---------------------------------------------------------------------------

def test_none_abstract_is_allowed():
    record = _valid_record(abstract=None)
    assert record.abstract is None


def test_no_invented_abstract():
    record = _valid_record(abstract=None)
    assert record.abstract is None


# ---------------------------------------------------------------------------
# 11. Empty authors allowed
# ---------------------------------------------------------------------------

def test_empty_authors_list_is_allowed():
    record = _valid_record(authors=[])
    assert record.authors == []


def test_multiple_authors_preserved():
    authors = ["Smith J", "Jones K", "Brown L"]
    record = _valid_record(authors=authors)
    assert record.authors == authors


# ---------------------------------------------------------------------------
# 12. Timezone-aware retrieved_at accepted
# ---------------------------------------------------------------------------

def test_utc_retrieved_at_accepted():
    record = _valid_record(retrieved_at=datetime.now(timezone.utc))
    assert record.retrieved_at.tzinfo is not None


def test_non_utc_timezone_aware_accepted():
    tz = timezone(timedelta(hours=5))
    record = _valid_record(retrieved_at=datetime.now(tz))
    assert record.retrieved_at.tzinfo is not None


# ---------------------------------------------------------------------------
# 13. Naive retrieved_at is rejected
# ---------------------------------------------------------------------------

def test_naive_retrieved_at_is_rejected():
    with pytest.raises(Exception):
        _valid_record(retrieved_at=datetime(2023, 6, 15, 12, 0, 0))


# ---------------------------------------------------------------------------
# 14. source_url is preserved
# ---------------------------------------------------------------------------

def test_source_url_preserved():
    url = "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    record = _valid_record(source_url=url)
    assert record.source_url == url


def test_none_source_url_allowed():
    record = _valid_record(source_url=None)
    assert record.source_url is None


# ---------------------------------------------------------------------------
# 15. Immutability
# ---------------------------------------------------------------------------

def test_literature_record_title_is_immutable():
    record = _valid_record()
    with pytest.raises(Exception):
        record.title = "Mutated Title"


def test_literature_record_doi_is_immutable():
    record = _valid_record()
    with pytest.raises(Exception):
        record.doi = "10.9999/mutated"


def test_literature_record_source_is_immutable():
    record = _valid_record()
    with pytest.raises(Exception):
        record.source = ExternalSource.CROSSREF


def test_literature_record_source_record_id_is_immutable():
    record = _valid_record()
    with pytest.raises(Exception):
        record.source_record_id = "MUTATED123"


def test_literature_record_retrieved_at_is_immutable():
    record = _valid_record()
    with pytest.raises(Exception):
        record.retrieved_at = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# 16 & 17. No external API or AI invoked (structural)
# ---------------------------------------------------------------------------

def test_no_http_calls_on_creation(monkeypatch):
    import urllib.request
    original = urllib.request.urlopen
    called = []

    def mock_urlopen(*args, **kwargs):
        called.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    _valid_record()
    assert called == []


def test_literature_record_has_no_api_methods():
    record = _valid_record()
    for forbidden in ("fetch", "retrieve", "search", "call_api", "generate"):
        assert not callable(getattr(record, forbidden, None))


# ---------------------------------------------------------------------------
# Public API import
# ---------------------------------------------------------------------------

def test_external_source_importable_from_domain():
    from domain import ExternalSource
    assert ExternalSource is not None


def test_literature_record_importable_from_domain():
    from domain import LiteratureRecord
    assert LiteratureRecord is not None


def test_external_source_in_domain_all():
    import domain
    assert "ExternalSource" in domain.__all__
    assert "LiteratureRecord" in domain.__all__


# ---------------------------------------------------------------------------
# Title validation
# ---------------------------------------------------------------------------

def test_empty_title_is_rejected():
    with pytest.raises(Exception):
        _valid_record(title="")


def test_whitespace_title_is_rejected():
    with pytest.raises(Exception):
        _valid_record(title="   ")


# ---------------------------------------------------------------------------
# Journal optional
# ---------------------------------------------------------------------------

def test_none_journal_is_allowed():
    record = _valid_record(journal=None)
    assert record.journal is None
