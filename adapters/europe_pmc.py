"""Europe PMC source adapter — official REST API implementation."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

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

_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_DEFAULT_MAX_RESULTS = 100
_DEFAULT_TIMEOUT = 30
_USER_AGENT = "ResearchCopilot/1.0 (https://github.com/research-copilot)"


class EuropePMCAdapter(LiteratureSourceAdapter):
    """
    Retrieves real literature records via the official Europe PMC REST API.

    Never invents records.
    Never modifies the supplied search strategy.
    All HTTP is bounded by timeout and result limit.
    """

    def __init__(
        self,
        max_results: int = _DEFAULT_MAX_RESULTS,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._max_results = max_results
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public contract
    # ------------------------------------------------------------------

    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        retrieved_at = datetime.now(timezone.utc)
        query = strategy.boolean_query or ""

        raw_results = self._query_api(query)

        records: list[LiteratureRecord] = []
        for item in raw_results:
            record = self._map_record(item, retrieved_at)
            if record is not None:
                records.append(record)

        return LiteratureSearchResult(
            source=ExternalSource.EUROPE_PMC,
            records=records,
            retrieved_at=retrieved_at,
            query=query,
        )

    # ------------------------------------------------------------------
    # API query
    # ------------------------------------------------------------------

    def _query_api(self, query: str) -> list[dict]:
        params: dict[str, str] = {
            "query": query,
            "pageSize": str(self._max_results),
            "format": "json",
            "resultType": "core",
        }
        url = f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}"

        try:
            raw = self._get(url)
        except LiteratureSourceError:
            raise
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.EUROPE_PMC,
                f"Europe PMC request failed: {exc}",
            ) from exc

        try:
            data = json.loads(raw)
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.EUROPE_PMC,
                f"Europe PMC response could not be parsed as JSON: {exc}",
            ) from exc

        try:
            result_list = data.get("resultList", {})
            if not isinstance(result_list, dict):
                raise LiteratureSourceError(
                    ExternalSource.EUROPE_PMC,
                    "Europe PMC response missing expected 'resultList' structure.",
                )
            results: list[dict] = result_list.get("result", [])
            if not isinstance(results, list):
                raise LiteratureSourceError(
                    ExternalSource.EUROPE_PMC,
                    "Europe PMC 'result' field is not a list.",
                )
            return results
        except LiteratureSourceError:
            raise
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.EUROPE_PMC,
                f"Europe PMC response structure unexpected: {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # Record mapping
    # ------------------------------------------------------------------

    def _map_record(
        self, item: dict, retrieved_at: datetime
    ) -> LiteratureRecord | None:
        # source_record_id — use Europe PMC's own 'id' field
        source_record_id = str(item.get("id", "")).strip()
        if not source_record_id:
            raise LiteratureSourceError(
                ExternalSource.EUROPE_PMC,
                "Europe PMC record is missing its provider identifier.",
            )

        # Title — required
        title = str(item.get("title", "")).strip()
        if not title:
            raise LiteratureSourceError(
                ExternalSource.EUROPE_PMC,
                f"Europe PMC record {source_record_id} has no valid title.",
            )

        # Authors
        authors = self._extract_authors(item)

        # Journal
        journal: str | None = item.get("journalTitle") or None
        if journal:
            journal = journal.strip() or None

        # Publication date
        pub_date: str | None = self._extract_pub_date(item)

        # Abstract
        abstract_raw = item.get("abstractText") or item.get("abstract") or None
        abstract: str | None = (
            abstract_raw.strip() if isinstance(abstract_raw, str) and abstract_raw.strip()
            else None
        )

        # DOI
        doi_raw = item.get("doi") or None
        doi: str | None = (
            doi_raw.strip() if isinstance(doi_raw, str) and doi_raw.strip()
            else None
        )

        # PMID — may or may not be present
        pmid_raw = item.get("pmid") or None
        pmid: str | None = (
            str(pmid_raw).strip() if pmid_raw and str(pmid_raw).strip()
            else None
        )

        # Source URL — constructed from actual provider identifier only
        source_url = (
            f"https://europepmc.org/article/{item.get('source', 'MED')}"
            f"/{source_record_id}"
        )

        return LiteratureRecord(
            title=title,
            authors=authors,
            journal=journal,
            publication_date=pub_date,
            abstract=abstract,
            doi=doi,
            pmid=pmid,
            source=ExternalSource.EUROPE_PMC,
            source_record_id=source_record_id,
            source_url=source_url,
            retrieved_at=retrieved_at,
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_authors(self, item: dict) -> list[str]:
        authors: list[str] = []

        # Prefer structured authorList
        author_list = item.get("authorList") or {}
        if isinstance(author_list, dict):
            for author in author_list.get("author", []):
                if isinstance(author, dict):
                    full = author.get("fullName", "").strip()
                    if full:
                        authors.append(full)
                        continue
                    last = author.get("lastName", "").strip()
                    first = author.get("firstName", "").strip()
                    initials = author.get("initials", "").strip()
                    if last:
                        name = f"{last} {first}" if first else (
                            f"{last} {initials}" if initials else last
                        )
                        authors.append(name)

        # Fallback: flat authorString
        if not authors:
            author_string = item.get("authorString", "").strip()
            if author_string:
                authors = [a.strip() for a in author_string.split(",") if a.strip()]

        return authors

    def _extract_pub_date(self, item: dict) -> str | None:
        # Prefer firstPublicationDate, then pubYear
        first_pub = item.get("firstPublicationDate", "").strip()
        if first_pub:
            return first_pub

        pub_year = item.get("pubYear") or item.get("publicationYear") or None
        if pub_year:
            return str(pub_year).strip() or None

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
                ExternalSource.EUROPE_PMC,
                f"HTTP {exc.code} from Europe PMC: {exc.reason}",
            ) from exc
        except urllib.error.URLError as exc:
            raise LiteratureSourceError(
                ExternalSource.EUROPE_PMC,
                f"Network error reaching Europe PMC: {exc.reason}",
            ) from exc
        except TimeoutError as exc:
            raise LiteratureSourceError(
                ExternalSource.EUROPE_PMC,
                "Europe PMC request timed out.",
            ) from exc
