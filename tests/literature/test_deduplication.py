"""Tests for LiteratureDeduplicator — fully deterministic and offline."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from domain.literature import ExternalSource, LiteratureRecord
from literature.deduplication import (
    DeduplicatedLiteratureCollection,
    DuplicateGroup,
    LiteratureDeduplicator,
    _normalize_doi,
    _normalize_title,
    _extract_year,
)
from services.literature_source import LiteratureSearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _rec(
    source: ExternalSource = ExternalSource.PUBMED,
    title: str = "A Study",
    doi: str | None = None,
    pmid: str | None = None,
    pub_date: str | None = None,
    journal: str | None = None,
    abstract: str | None = None,
    authors: list[str] | None = None,
) -> LiteratureRecord:
    return LiteratureRecord(
        title=title,
        source=source,
        source_record_id=str(uuid4()),
        doi=doi,
        pmid=pmid,
        publication_date=pub_date,
        journal=journal,
        abstract=abstract,
        authors=authors or [],
        retrieved_at=_utc(),
    )


def _result(
    source: ExternalSource,
    records: list[LiteratureRecord],
) -> LiteratureSearchResult:
    return LiteratureSearchResult(
        source=source,
        records=records,
        retrieved_at=_utc(),
        query="query",
    )


dedup = LiteratureDeduplicator()


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def test_normalize_doi_strips_https_prefix():
    assert _normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"


def test_normalize_doi_strips_http_prefix():
    assert _normalize_doi("http://doi.org/10.1000/abc") == "10.1000/abc"


def test_normalize_doi_strips_doi_colon_prefix():
    assert _normalize_doi("doi:10.1000/ABC") == "10.1000/abc"


def test_normalize_doi_bare_doi():
    assert _normalize_doi("10.1000/ABC") == "10.1000/abc"


def test_normalize_doi_case_insensitive():
    assert _normalize_doi("10.1000/ABC") == _normalize_doi("10.1000/abc")


def test_normalize_doi_none_returns_none():
    assert _normalize_doi(None) is None


def test_normalize_doi_empty_returns_none():
    assert _normalize_doi("") is None


def test_normalize_title_lowercases():
    assert _normalize_title("Metformin Study") == "metformin study"


def test_normalize_title_collapses_whitespace():
    assert _normalize_title("  metformin   study  ") == "metformin study"


def test_normalize_title_none_returns_none():
    assert _normalize_title(None) is None


def test_extract_year_from_full_date():
    assert _extract_year("2023-05-14") == "2023"


def test_extract_year_from_year_only():
    assert _extract_year("2025") == "2025"


def test_extract_year_none_returns_none():
    assert _extract_year(None) is None


def test_extract_year_invalid_returns_none():
    assert _extract_year("unknown") is None


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_empty_results_returns_empty_collection():
    result = dedup.deduplicate([])
    assert isinstance(result, DeduplicatedLiteratureCollection)
    assert result.groups == []
    assert result.total_unique == 0


def test_empty_records_in_results():
    r = _result(ExternalSource.PUBMED, records=[])
    collection = dedup.deduplicate([r])
    assert collection.total_unique == 0


# ---------------------------------------------------------------------------
# Single unique record
# ---------------------------------------------------------------------------

def test_single_record_returns_one_group():
    rec = _rec(doi="10.1000/abc")
    r = _result(ExternalSource.PUBMED, records=[rec])
    collection = dedup.deduplicate([r])
    assert collection.total_unique == 1


def test_single_record_no_duplicates():
    rec = _rec(doi="10.1000/abc")
    r = _result(ExternalSource.PUBMED, records=[rec])
    collection = dedup.deduplicate([r])
    assert collection.groups[0].duplicate_records == []


def test_single_record_metadata_unchanged():
    rec = _rec(title="Original Title", doi="10.1000/abc")
    r = _result(ExternalSource.PUBMED, records=[rec])
    collection = dedup.deduplicate([r])
    assert collection.groups[0].canonical_record.title == "Original Title"


# ---------------------------------------------------------------------------
# TEST 18: DOI duplicate
# ---------------------------------------------------------------------------

def test_doi_duplicate_detected():
    r1 = _rec(source=ExternalSource.PUBMED, doi="10.1000/ABC", title="Study A")
    r2 = _rec(source=ExternalSource.CROSSREF, doi="https://doi.org/10.1000/abc", title="Study A")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    assert collection.total_unique == 1


def test_doi_duplicate_one_canonical_one_duplicate():
    r1 = _rec(source=ExternalSource.PUBMED, doi="10.1000/ABC")
    r2 = _rec(source=ExternalSource.CROSSREF, doi="https://doi.org/10.1000/abc")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    assert len(collection.groups[0].duplicate_records) == 1


def test_doi_mixed_case_same_work():
    r1 = _rec(doi="10.1000/XYZ")
    r2 = _rec(doi="10.1000/xyz")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.EUROPE_PMC, [r2]),
    ])
    assert collection.total_unique == 1


def test_doi_different_works_stay_separate():
    r1 = _rec(doi="10.1000/AAA")
    r2 = _rec(doi="10.1000/BBB")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    assert collection.total_unique == 2


# ---------------------------------------------------------------------------
# TEST 19: PMID duplicate
# ---------------------------------------------------------------------------

def test_pmid_duplicate_detected():
    r1 = _rec(source=ExternalSource.PUBMED, pmid="123456", title="Study P")
    r2 = _rec(source=ExternalSource.EUROPE_PMC, pmid="123456", title="Study P")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.EUROPE_PMC, [r2]),
    ])
    assert collection.total_unique == 1


def test_pmid_different_values_stay_separate():
    r1 = _rec(pmid="111111")
    r2 = _rec(pmid="222222")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.EUROPE_PMC, [r2]),
    ])
    assert collection.total_unique == 2


def test_pmid_duplicate_preserves_provenance():
    r1 = _rec(source=ExternalSource.PUBMED, pmid="999999")
    r2 = _rec(source=ExternalSource.EUROPE_PMC, pmid="999999")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.EUROPE_PMC, [r2]),
    ])
    sources = collection.groups[0].sources
    assert ExternalSource.PUBMED in sources
    assert ExternalSource.EUROPE_PMC in sources


# ---------------------------------------------------------------------------
# TEST 20: Title + year duplicate
# ---------------------------------------------------------------------------

def test_title_year_duplicate_detected():
    r1 = _rec(
        source=ExternalSource.OPENALEX,
        title="Metformin and Cardiovascular Outcomes",
        pub_date="2025-01-15",
    )
    r2 = _rec(
        source=ExternalSource.CROSSREF,
        title=" metformin   and cardiovascular outcomes ",
        pub_date="2025",
    )
    collection = dedup.deduplicate([
        _result(ExternalSource.OPENALEX, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    assert collection.total_unique == 1


def test_title_year_same_title_different_year_stays_separate():
    r1 = _rec(
        title="Aspirin and Stroke Prevention",
        pub_date="2024",
    )
    r2 = _rec(
        title="Aspirin and Stroke Prevention",
        pub_date="2025",
    )
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.EUROPE_PMC, [r2]),
    ])
    assert collection.total_unique == 2


def test_title_year_missing_year_not_matched():
    r1 = _rec(title="Study With No Date")
    r2 = _rec(title="Study With No Date")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    # Without year, title-only matching is not applied → stay separate
    assert collection.total_unique == 2


# ---------------------------------------------------------------------------
# TEST 21: Different years → separate works
# ---------------------------------------------------------------------------

def test_same_title_different_years_remain_separate():
    r1 = _rec(title="A Long-Term Study", pub_date="2024-06-01")
    r2 = _rec(title="A Long-Term Study", pub_date="2025-06-01")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.EUROPE_PMC, [r2]),
    ])
    assert collection.total_unique == 2


# ---------------------------------------------------------------------------
# TEST 22: DOI overrides title difference
# ---------------------------------------------------------------------------

def test_doi_match_overrides_title_difference():
    r1 = _rec(doi="10.2222/study", title="Original Title")
    r2 = _rec(doi="10.2222/study", title="A Completely Different Title")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    assert collection.total_unique == 1


# ---------------------------------------------------------------------------
# TEST 23: No fuzzy matching
# ---------------------------------------------------------------------------

def test_similar_titles_not_merged():
    r1 = _rec(title="Metformin and cardiovascular outcomes", pub_date="2023")
    r2 = _rec(title="Metformin treatment and cardiovascular outcomes", pub_date="2023")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.EUROPE_PMC, [r2]),
    ])
    assert collection.total_unique == 2


def test_substring_title_not_merged():
    r1 = _rec(title="Aspirin therapy", pub_date="2022")
    r2 = _rec(title="Aspirin therapy for secondary prevention", pub_date="2022")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    assert collection.total_unique == 2


# ---------------------------------------------------------------------------
# TEST 24: Provenance
# ---------------------------------------------------------------------------

def test_four_provider_provenance_preserved():
    doi = "10.9999/shared"
    r_pub = _rec(source=ExternalSource.PUBMED, doi=doi)
    r_epm = _rec(source=ExternalSource.EUROPE_PMC, doi=doi)
    r_oal = _rec(source=ExternalSource.OPENALEX, doi=doi)
    r_crf = _rec(source=ExternalSource.CROSSREF, doi=doi)
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r_pub]),
        _result(ExternalSource.EUROPE_PMC, [r_epm]),
        _result(ExternalSource.OPENALEX, [r_oal]),
        _result(ExternalSource.CROSSREF, [r_crf]),
    ])
    assert collection.total_unique == 1
    sources = collection.groups[0].sources
    assert ExternalSource.PUBMED in sources
    assert ExternalSource.EUROPE_PMC in sources
    assert ExternalSource.OPENALEX in sources
    assert ExternalSource.CROSSREF in sources


def test_provenance_all_records_accessible():
    doi = "10.1111/multi"
    r1 = _rec(source=ExternalSource.PUBMED, doi=doi)
    r2 = _rec(source=ExternalSource.CROSSREF, doi=doi)
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    group = collection.groups[0]
    assert len(group.all_records) == 2


# ---------------------------------------------------------------------------
# TEST 25: Representative selection
# ---------------------------------------------------------------------------

def test_representative_with_doi_preferred_over_no_doi():
    r_no_doi = _rec(source=ExternalSource.CROSSREF, pmid="555", title="Study")
    r_with_doi = _rec(source=ExternalSource.CROSSREF, doi="10.5/study", pmid="555", title="Study")
    collection = dedup.deduplicate([
        _result(ExternalSource.CROSSREF, [r_no_doi, r_with_doi]),
    ])
    # should only be one group (pmid match) with doi-bearing record as canonical
    assert collection.groups[0].canonical_record.doi == "10.5/study"


def test_source_priority_pubmed_over_crossref():
    doi = "10.3333/test"
    r_crf = _rec(source=ExternalSource.CROSSREF, doi=doi, title="Study")
    r_pub = _rec(source=ExternalSource.PUBMED, doi=doi, title="Study")
    collection = dedup.deduplicate([
        _result(ExternalSource.CROSSREF, [r_crf]),
        _result(ExternalSource.PUBMED, [r_pub]),
    ])
    assert collection.groups[0].canonical_record.source == ExternalSource.PUBMED


def test_source_priority_pubmed_over_europe_pmc():
    doi = "10.4444/test"
    r_epm = _rec(source=ExternalSource.EUROPE_PMC, doi=doi)
    r_pub = _rec(source=ExternalSource.PUBMED, doi=doi)
    collection = dedup.deduplicate([
        _result(ExternalSource.EUROPE_PMC, [r_epm]),
        _result(ExternalSource.PUBMED, [r_pub]),
    ])
    assert collection.groups[0].canonical_record.source == ExternalSource.PUBMED


def test_source_priority_europe_pmc_over_openalex():
    doi = "10.5555/test"
    r_oal = _rec(source=ExternalSource.OPENALEX, doi=doi)
    r_epm = _rec(source=ExternalSource.EUROPE_PMC, doi=doi)
    collection = dedup.deduplicate([
        _result(ExternalSource.OPENALEX, [r_oal]),
        _result(ExternalSource.EUROPE_PMC, [r_epm]),
    ])
    assert collection.groups[0].canonical_record.source == ExternalSource.EUROPE_PMC


def test_source_priority_openalex_over_crossref():
    doi = "10.6666/test"
    r_crf = _rec(source=ExternalSource.CROSSREF, doi=doi)
    r_oal = _rec(source=ExternalSource.OPENALEX, doi=doi)
    collection = dedup.deduplicate([
        _result(ExternalSource.CROSSREF, [r_crf]),
        _result(ExternalSource.OPENALEX, [r_oal]),
    ])
    assert collection.groups[0].canonical_record.source == ExternalSource.OPENALEX


# ---------------------------------------------------------------------------
# TEST 26: Input order as stable tie-breaker
# ---------------------------------------------------------------------------

def test_input_order_stable_tiebreaker():
    # Two Crossref records with same DOI: first one should win
    doi = "10.7777/tiebreak"
    r1 = _rec(source=ExternalSource.CROSSREF, doi=doi, title="First")
    r2 = _rec(source=ExternalSource.CROSSREF, doi=doi, title="Second")
    collection = dedup.deduplicate([
        _result(ExternalSource.CROSSREF, [r1, r2]),
    ])
    # Both from same source/completeness — first input position wins
    assert collection.groups[0].canonical_record.title == "First"


# ---------------------------------------------------------------------------
# TEST 27: No metadata invention
# ---------------------------------------------------------------------------

def test_deduplication_never_creates_doi():
    r1 = _rec(title="Study X", pub_date="2022")
    r2 = _rec(title="study x", pub_date="2022")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    for group in collection.groups:
        for rec in group.all_records:
            assert rec.doi is None


def test_deduplication_never_creates_pmid():
    r = _rec(title="Study Y", pub_date="2021")
    collection = dedup.deduplicate([_result(ExternalSource.PUBMED, [r])])
    assert collection.groups[0].canonical_record.pmid is None


def test_deduplication_does_not_alter_title():
    original_title = "Exact Original Title"
    r = _rec(title=original_title, doi="10.1/exact")
    collection = dedup.deduplicate([_result(ExternalSource.PUBMED, [r])])
    assert collection.groups[0].canonical_record.title == original_title


# ---------------------------------------------------------------------------
# TEST 28: Idempotence
# ---------------------------------------------------------------------------

def test_deduplication_idempotent():
    r1 = _rec(source=ExternalSource.PUBMED, doi="10.1000/idemp", title="Study")
    r2 = _rec(source=ExternalSource.CROSSREF, doi="10.1000/idemp", title="Study")

    first_pass = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    assert first_pass.total_unique == 1

    # Run again using canonical records only
    canonical = first_pass.groups[0].canonical_record
    second_pass = dedup.deduplicate([
        _result(canonical.source, [canonical]),
    ])
    assert second_pass.total_unique == 1
    assert second_pass.groups[0].duplicate_records == []


# ---------------------------------------------------------------------------
# Multiple unique works preserved
# ---------------------------------------------------------------------------

def test_three_unique_works_stay_separate():
    r1 = _rec(doi="10.1/aaa", title="Study A", pub_date="2021")
    r2 = _rec(doi="10.1/bbb", title="Study B", pub_date="2022")
    r3 = _rec(doi="10.1/ccc", title="Study C", pub_date="2023")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1, r2, r3]),
    ])
    assert collection.total_unique == 3


def test_total_input_records_counted_correctly():
    r1 = _rec(doi="10.1/x")
    r2 = _rec(doi="10.1/x")  # duplicate
    r3 = _rec(doi="10.1/y")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.EUROPE_PMC, [r2, r3]),
    ])
    assert collection.total_input_records == 3
    assert collection.total_unique == 2


# ---------------------------------------------------------------------------
# Conflicting metadata not silently merged
# ---------------------------------------------------------------------------

def test_conflicting_titles_not_merged_into_canonical():
    doi = "10.8888/conflict"
    r1 = _rec(source=ExternalSource.PUBMED, doi=doi, title="Metformin and cardiovascular outcomes")
    r2 = _rec(source=ExternalSource.CROSSREF, doi=doi, title="Metformin and cardiovascular outcomes: a review")
    collection = dedup.deduplicate([
        _result(ExternalSource.PUBMED, [r1]),
        _result(ExternalSource.CROSSREF, [r2]),
    ])
    group = collection.groups[0]
    # Both titles remain accessible — not merged
    all_titles = {rec.title for rec in group.all_records}
    assert "Metformin and cardiovascular outcomes" in all_titles
    assert "Metformin and cardiovascular outcomes: a review" in all_titles


# ---------------------------------------------------------------------------
# No AI / No external calls
# ---------------------------------------------------------------------------

def test_no_ai_imports_in_deduplication():
    import inspect
    import literature.deduplication as mod
    source = inspect.getsource(mod)
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "gemini" not in source.lower()


def test_no_http_in_deduplication():
    import inspect
    import literature.deduplication as mod
    source = inspect.getsource(mod)
    assert "urllib.request.urlopen" not in source
    assert "requests" not in source


# ---------------------------------------------------------------------------
# Public imports
# ---------------------------------------------------------------------------

def test_deduplicator_importable_from_literature():
    from literature import LiteratureDeduplicator
    assert LiteratureDeduplicator is not None


def test_deduplicated_collection_importable():
    from literature import DeduplicatedLiteratureCollection
    assert DeduplicatedLiteratureCollection is not None


def test_duplicate_group_importable():
    from literature import DuplicateGroup
    assert DuplicateGroup is not None
