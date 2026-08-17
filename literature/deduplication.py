"""Deterministic literature deduplication engine."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Sequence

from domain.literature import ExternalSource, LiteratureRecord
from services.literature_source import LiteratureSearchResult

# ---------------------------------------------------------------------------
# Source priority for representative selection (lower index = higher priority)
# ---------------------------------------------------------------------------

_SOURCE_PRIORITY: dict[ExternalSource, int] = {
    ExternalSource.PUBMED: 0,
    ExternalSource.EUROPE_PMC: 1,
    ExternalSource.OPENALEX: 2,
    ExternalSource.CROSSREF: 3,
}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_doi(doi: str | None) -> str | None:
    """Return a lowercase, prefix-stripped DOI for comparison only."""
    if not doi:
        return None
    d = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d or None


def _normalize_pmid(pmid: str | None) -> str | None:
    if not pmid:
        return None
    stripped = pmid.strip()
    return stripped if stripped else None


def _normalize_title(title: str | None) -> str | None:
    """
    Deterministic title normalization.

    - Strip surrounding whitespace
    - Lowercase
    - Collapse repeated whitespace
    - Normalize unicode to NFC
    - Remove leading/trailing punctuation artifacts

    Does NOT stem, translate, summarize, or use AI.
    """
    if not title:
        return None
    t = unicodedata.normalize("NFC", title)
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t or None


def _normalize_journal(journal: str | None) -> str | None:
    if not journal:
        return None
    return re.sub(r"\s+", " ", journal.lower().strip()) or None


def _extract_year(pub_date: str | None) -> str | None:
    """Extract a 4-digit year from a publication_date string."""
    if not pub_date:
        return None
    match = re.search(r"\b(1[89]\d{2}|20\d{2})\b", pub_date)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Domain structures
# ---------------------------------------------------------------------------

@dataclass
class DuplicateGroup:
    """
    One canonical scholarly work with full source provenance.

    canonical_record : the chosen representative
    duplicate_records: all other provider records for the same work
    sources          : every provider that returned this work
    """
    canonical_record: LiteratureRecord
    duplicate_records: list[LiteratureRecord] = field(default_factory=list)

    @property
    def sources(self) -> list[ExternalSource]:
        all_records = [self.canonical_record] + self.duplicate_records
        seen: list[ExternalSource] = []
        for r in all_records:
            if r.source not in seen:
                seen.append(r.source)
        return seen

    @property
    def all_records(self) -> list[LiteratureRecord]:
        return [self.canonical_record] + self.duplicate_records


@dataclass
class DeduplicatedLiteratureCollection:
    """Result of the deduplication pass."""
    groups: list[DuplicateGroup] = field(default_factory=list)

    @property
    def canonical_records(self) -> list[LiteratureRecord]:
        return [g.canonical_record for g in self.groups]

    @property
    def total_unique(self) -> int:
        return len(self.groups)

    @property
    def total_input_records(self) -> int:
        return sum(len(g.all_records) for g in self.groups)


# ---------------------------------------------------------------------------
# Deduplicator
# ---------------------------------------------------------------------------

class LiteratureDeduplicator:
    """
    Deterministic literature deduplication engine.

    Priority:
      1. DOI (case-insensitive, prefix-stripped)
      2. PMID
      3. Normalized title + publication year

    Never uses fuzzy matching, embeddings, or AI.
    Never invents metadata.
    Preserves full source provenance.
    """

    def deduplicate(
        self,
        results: Sequence[LiteratureSearchResult],
    ) -> DeduplicatedLiteratureCollection:
        # Collect all records in stable input order with their position index
        indexed: list[tuple[int, LiteratureRecord]] = []
        pos = 0
        for result in results:
            for record in result.records:
                indexed.append((pos, record))
                pos += 1

        if not indexed:
            return DeduplicatedLiteratureCollection()

        # group_id → list of (original_pos, record)
        groups: dict[int, list[tuple[int, LiteratureRecord]]] = {}
        # record position → group_id
        assignment: dict[int, int] = {}
        next_group = 0

        for original_pos, record in indexed:
            matched_group = self._find_matching_group(
                record, indexed, assignment, groups
            )
            if matched_group is None:
                groups[next_group] = [(original_pos, record)]
                assignment[original_pos] = next_group
                next_group += 1
            else:
                groups[matched_group].append((original_pos, record))
                assignment[original_pos] = matched_group

        collection = DeduplicatedLiteratureCollection()
        for gid in sorted(groups.keys()):
            members = groups[gid]
            canonical = self._select_representative(members)
            others = [r for (_, r) in members if r is not canonical]
            collection.groups.append(
                DuplicateGroup(canonical_record=canonical, duplicate_records=others)
            )

        return collection

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def _find_matching_group(
        self,
        record: LiteratureRecord,
        indexed: list[tuple[int, LiteratureRecord]],
        assignment: dict[int, int],
        groups: dict[int, list[tuple[int, LiteratureRecord]]],
    ) -> int | None:
        """
        Return the group id of an already-assigned record that matches,
        or None if this is a new unique work.
        """
        doi_key = _normalize_doi(record.doi)
        pmid_key = _normalize_pmid(record.pmid)
        title_key = _normalize_title(record.title)
        year_key = _extract_year(record.publication_date)

        for assigned_pos, assigned_record in indexed:
            if assigned_pos not in assignment:
                # not yet assigned — skip
                continue
            if self._is_duplicate(
                record, doi_key, pmid_key, title_key, year_key, assigned_record
            ):
                return assignment[assigned_pos]
        return None

    def _is_duplicate(
        self,
        a: LiteratureRecord,
        doi_key_a: str | None,
        pmid_key_a: str | None,
        title_key_a: str | None,
        year_key_a: str | None,
        b: LiteratureRecord,
    ) -> bool:
        # Priority 1: DOI
        doi_key_b = _normalize_doi(b.doi)
        if doi_key_a and doi_key_b:
            return doi_key_a == doi_key_b

        # Priority 2: PMID
        pmid_key_b = _normalize_pmid(b.pmid)
        if pmid_key_a and pmid_key_b:
            return pmid_key_a == pmid_key_b

        # Priority 3: title + year (both must be present)
        title_key_b = _normalize_title(b.title)
        year_key_b = _extract_year(b.publication_date)
        if title_key_a and title_key_b and year_key_a and year_key_b:
            if title_key_a == title_key_b and year_key_a == year_key_b:
                return True

        return False

    # ------------------------------------------------------------------
    # Representative selection
    # ------------------------------------------------------------------

    def _select_representative(
        self, members: list[tuple[int, LiteratureRecord]]
    ) -> LiteratureRecord:
        """
        Deterministic representative selection.

        Order:
        1. Has DOI
        2. Has PMID
        3. More complete metadata (more non-None fields)
        4. Source priority (PubMed > EuropePMC > OpenAlex > Crossref)
        5. Original input position (stable tie-breaker)
        """

        def _completeness(r: LiteratureRecord) -> int:
            fields = [r.doi, r.pmid, r.abstract, r.journal,
                      r.publication_date, r.authors]
            return sum(1 for f in fields if f)

        def _sort_key(item: tuple[int, LiteratureRecord]):
            pos, r = item
            has_doi = 0 if r.doi else 1
            has_pmid = 0 if r.pmid else 1
            completeness = -_completeness(r)  # higher is better → negate
            source_rank = _SOURCE_PRIORITY.get(r.source, 99)
            return (has_doi, has_pmid, completeness, source_rank, pos)

        best_pos, best_record = min(members, key=_sort_key)
        return best_record
