"""PubMed source adapter — NCBI E-utilities implementation."""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

from domain.literature import ExternalSource, LiteratureRecord
from domain.literature_search import LiteratureSearchStrategy
from services.literature_source import (
    LiteratureSearchResult,
    LiteratureSourceAdapter,
    LiteratureSourceError,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_DEFAULT_MAX_RESULTS = 100
_DEFAULT_TIMEOUT = 30
_USER_AGENT = "ResearchCopilot/1.0 (https://github.com/research-copilot)"


class PubMedAdapter(LiteratureSourceAdapter):
    """
    Retrieves real PubMed records via NCBI E-utilities.

    Never invents records.
    Never modifies the supplied search strategy.
    All HTTP is bounded by timeout and result limit.
    """

    def __init__(
        self,
        max_results: int = _DEFAULT_MAX_RESULTS,
        timeout: int = _DEFAULT_TIMEOUT,
        tool: str = "ResearchCopilot",
        email: str | None = None,
    ) -> None:
        self._max_results = max_results
        self._timeout = timeout
        self._tool = tool
        self._email = email

    # ------------------------------------------------------------------
    # Public contract
    # ------------------------------------------------------------------

    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        retrieved_at = datetime.now(timezone.utc)
        query = strategy.boolean_query or ""

        pmids = self._esearch(query)

        if not pmids:
            return LiteratureSearchResult(
                source=ExternalSource.PUBMED,
                records=[],
                retrieved_at=retrieved_at,
                query=query,
            )

        records = self._efetch(pmids, retrieved_at)

        return LiteratureSearchResult(
            source=ExternalSource.PUBMED,
            records=records,
            retrieved_at=retrieved_at,
            query=query,
        )

    # ------------------------------------------------------------------
    # ESearch
    # ------------------------------------------------------------------

    def _esearch(self, query: str) -> list[str]:
        params: dict[str, str] = {
            "db": "pubmed",
            "term": query,
            "retmax": str(self._max_results),
            "retmode": "json",
            "tool": self._tool,
        }
        if self._email:
            params["email"] = self._email

        url = f"{_ESEARCH_URL}?{urllib.parse.urlencode(params)}"

        try:
            raw = self._get(url)
        except LiteratureSourceError:
            raise
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                f"ESearch request failed: {exc}",
            ) from exc

        try:
            import json
            data = json.loads(raw)
            id_list: list[str] = (
                data.get("esearchresult", {}).get("idlist", [])
            )
            return id_list
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                f"ESearch response could not be parsed: {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # EFetch
    # ------------------------------------------------------------------

    def _efetch(
        self, pmids: list[str], retrieved_at: datetime
    ) -> list[LiteratureRecord]:
        params: dict[str, str] = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "xml",
            "retmode": "xml",
            "tool": self._tool,
        }
        if self._email:
            params["email"] = self._email

        url = f"{_EFETCH_URL}?{urllib.parse.urlencode(params)}"

        try:
            raw = self._get(url)
        except LiteratureSourceError:
            raise
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                f"EFetch request failed: {exc}",
            ) from exc

        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                f"EFetch XML could not be parsed: {exc}",
            ) from exc

        records: list[LiteratureRecord] = []
        for article in root.findall(".//PubmedArticle"):
            record = self._map_article(article, retrieved_at)
            if record is not None:
                records.append(record)
        return records

    # ------------------------------------------------------------------
    # Article mapping
    # ------------------------------------------------------------------

    def _map_article(
        self, article: ET.Element, retrieved_at: datetime
    ) -> LiteratureRecord | None:
        medline = article.find("MedlineCitation")
        if medline is None:
            return None

        # PMID
        pmid_el = medline.find("PMID")
        if pmid_el is None or not (pmid_el.text or "").strip():
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                "PubMed record is missing PMID.",
            )
        pmid = pmid_el.text.strip()

        art = medline.find("Article")
        if art is None:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                f"PubMed record {pmid} has no Article element.",
            )

        # Title
        title_el = art.find("ArticleTitle")
        if title_el is None:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                f"PubMed record {pmid} is missing a title.",
            )
        title_text = "".join(title_el.itertext()).strip()
        if not title_text:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                f"PubMed record {pmid} has an empty title.",
            )

        # Authors
        authors = self._extract_authors(art)

        # Journal
        journal: str | None = None
        journal_el = art.find("Journal/Title")
        if journal_el is not None and journal_el.text:
            journal = journal_el.text.strip() or None

        # Publication date
        pub_date = self._extract_pub_date(art)

        # Abstract
        abstract = self._extract_abstract(art)

        # DOI
        doi: str | None = None
        for loc in article.findall(".//ArticleId"):
            if loc.get("IdType") == "doi" and loc.text:
                doi = loc.text.strip() or None
                break

        source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        return LiteratureRecord(
            title=title_text,
            authors=authors,
            journal=journal,
            publication_date=pub_date,
            abstract=abstract,
            doi=doi,
            pmid=pmid,
            source=ExternalSource.PUBMED,
            source_record_id=pmid,
            source_url=source_url,
            retrieved_at=retrieved_at,
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_authors(self, art: ET.Element) -> list[str]:
        authors: list[str] = []
        for author in art.findall("AuthorList/Author"):
            last = author.findtext("LastName", "").strip()
            fore = author.findtext("ForeName", "").strip()
            initials = author.findtext("Initials", "").strip()
            collective = author.findtext("CollectiveName", "").strip()
            if collective:
                authors.append(collective)
            elif last:
                name = last
                if fore:
                    name = f"{last} {fore}"
                elif initials:
                    name = f"{last} {initials}"
                authors.append(name)
        return authors

    def _extract_abstract(self, art: ET.Element) -> str | None:
        parts: list[str] = []
        for text_el in art.findall("Abstract/AbstractText"):
            label = text_el.get("Label")
            content = "".join(text_el.itertext()).strip()
            if content:
                parts.append(f"{label}: {content}" if label else content)
        return "\n".join(parts) if parts else None

    def _extract_pub_date(self, art: ET.Element) -> str | None:
        # Prefer ArticleDate, then JournalIssue/PubDate
        for date_el in art.findall("ArticleDate"):
            y = date_el.findtext("Year", "").strip()
            m = date_el.findtext("Month", "").strip()
            d = date_el.findtext("Day", "").strip()
            if y:
                parts = [p for p in (y, m, d) if p]
                return "-".join(parts)

        pub_date_el = art.find("Journal/JournalIssue/PubDate")
        if pub_date_el is not None:
            y = pub_date_el.findtext("Year", "").strip()
            m = pub_date_el.findtext("Month", "").strip()
            d = pub_date_el.findtext("Day", "").strip()
            med = pub_date_el.findtext("MedlineDate", "").strip()
            if y:
                parts = [p for p in (y, m, d) if p]
                return "-".join(parts)
            if med:
                return med

        return None

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _get(self, url: str) -> str:
        req = urllib.request.Request(
            url, headers={"User-Agent": _USER_AGENT}
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                f"HTTP {exc.code} from PubMed: {exc.reason}",
            ) from exc
        except urllib.error.URLError as exc:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                f"Network error reaching PubMed: {exc.reason}",
            ) from exc
        except TimeoutError as exc:
            raise LiteratureSourceError(
                ExternalSource.PUBMED,
                "PubMed request timed out.",
            ) from exc
