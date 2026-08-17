"""OpenAlex source adapter — official API implementation."""
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

_SEARCH_URL = "https://api.openalex.org/works"
_DEFAULT_MAX_RESULTS = 100
_DEFAULT_TIMEOUT = 30
_USER_AGENT = "ResearchCopilot/1.0 (https://github.com/research-copilot)"


class OpenAlexAdapter(LiteratureSourceAdapter):
    """
    Retrieves real scholarly work records via the official OpenAlex API.

    Never invents records.
    Never modifies the supplied search strategy.
    All HTTP is bounded by timeout and result limit.
    """

    def __init__(
        self,
        max_results: int = _DEFAULT_MAX_RESULTS,
        timeout: int = _DEFAULT_TIMEOUT,
        email: str | None = None,
    ) -> None:
        self._max_results = max_results
        self._timeout = timeout
        self._email = email

    # ------------------------------------------------------------------
    # Public contract
    # ------------------------------------------------------------------

    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        retrieved_at = datetime.now(timezone.utc)
        query = strategy.boolean_query or ""

        raw_works = self._query_api(query)

        records: list[LiteratureRecord] = []
        for work in raw_works:
            record = self._map_work(work, retrieved_at)
            if record is not None:
                records.append(record)

        return LiteratureSearchResult(
            source=ExternalSource.OPENALEX,
            records=records,
            retrieved_at=retrieved_at,
            query=query,
        )

    # ------------------------------------------------------------------
    # API query
    # ------------------------------------------------------------------

    def _query_api(self, query: str) -> list[dict]:
        params: dict[str, str] = {
            "search": query,
            "per_page": str(min(self._max_results, 200)),
        }
        if self._email:
            params["mailto"] = self._email

        url = f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}"

        try:
            raw = self._get(url)
        except LiteratureSourceError:
            raise
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.OPENALEX,
                f"OpenAlex request failed: {exc}",
            ) from exc

        try:
            data = json.loads(raw)
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.OPENALEX,
                f"OpenAlex response could not be parsed as JSON: {exc}",
            ) from exc

        try:
            results = data.get("results")
            if results is None:
                raise LiteratureSourceError(
                    ExternalSource.OPENALEX,
                    "OpenAlex response missing expected 'results' field.",
                )
            if not isinstance(results, list):
                raise LiteratureSourceError(
                    ExternalSource.OPENALEX,
                    "OpenAlex 'results' field is not a list.",
                )
            return results[: self._max_results]
        except LiteratureSourceError:
            raise
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.OPENALEX,
                f"OpenAlex response structure unexpected: {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # Work mapping
    # ------------------------------------------------------------------

    def _map_work(
        self, work: dict, retrieved_at: datetime
    ) -> LiteratureRecord | None:
        # OpenAlex ID — required
        openalex_id = str(work.get("id", "")).strip()
        if not openalex_id:
            raise LiteratureSourceError(
                ExternalSource.OPENALEX,
                "OpenAlex work is missing its provider identifier.",
            )

        # Use the short numeric portion as the canonical source_record_id
        source_record_id = openalex_id

        # Title — required
        title = str(work.get("title") or "").strip()
        if not title:
            raise LiteratureSourceError(
                ExternalSource.OPENALEX,
                f"OpenAlex work {openalex_id} has no valid title.",
            )

        # Authors
        authors = self._extract_authors(work)

        # Journal / venue
        journal: str | None = self._extract_journal(work)

        # Publication date
        pub_date: str | None = (
            str(work["publication_date"]).strip()
            if work.get("publication_date")
            else None
        )

        # Abstract — reconstruct from inverted index
        abstract: str | None = self._reconstruct_abstract(work)

        # DOI
        doi_raw = work.get("doi") or None
        doi: str | None = (
            str(doi_raw).replace("https://doi.org/", "").strip()
            if doi_raw
            else None
        ) or None

        # PMID — may be in ids dict
        pmid: str | None = None
        ids = work.get("ids") or {}
        pmid_raw = ids.get("pmid") or None
        if pmid_raw:
            pmid = str(pmid_raw).replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip() or None

        # Source URL
        source_url: str = openalex_id  # OpenAlex ID is already a URL

        return LiteratureRecord(
            title=title,
            authors=authors,
            journal=journal,
            publication_date=pub_date,
            abstract=abstract,
            doi=doi,
            pmid=pmid,
            source=ExternalSource.OPENALEX,
            source_record_id=source_record_id,
            source_url=source_url,
            retrieved_at=retrieved_at,
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_authors(self, work: dict) -> list[str]:
        authors: list[str] = []
        for authorship in work.get("authorships") or []:
            if not isinstance(authorship, dict):
                continue
            author_obj = authorship.get("author") or {}
            display_name = str(author_obj.get("display_name") or "").strip()
            if display_name:
                authors.append(display_name)
        return authors

    def _extract_journal(self, work: dict) -> str | None:
        # primary_location → source → display_name
        primary = work.get("primary_location") or {}
        if isinstance(primary, dict):
            source = primary.get("source") or {}
            if isinstance(source, dict):
                name = str(source.get("display_name") or "").strip()
                if name:
                    return name
        return None

    def _reconstruct_abstract(self, work: dict) -> str | None:
        """
        Reconstruct abstract from OpenAlex abstract_inverted_index.

        The inverted index maps word → list of positions.
        We deterministically rebuild the original word order.
        Words are preserved exactly; no summarization or rewriting.
        """
        inverted = work.get("abstract_inverted_index")
        if not inverted or not isinstance(inverted, dict):
            return None

        try:
            # Build position → word map
            position_word: dict[int, str] = {}
            for word, positions in inverted.items():
                if isinstance(positions, list):
                    for pos in positions:
                        position_word[int(pos)] = word

            if not position_word:
                return None

            ordered = [position_word[i] for i in sorted(position_word)]
            return " ".join(ordered)
        except Exception:
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
                ExternalSource.OPENALEX,
                f"HTTP {exc.code} from OpenAlex: {exc.reason}",
            ) from exc
        except urllib.error.URLError as exc:
            raise LiteratureSourceError(
                ExternalSource.OPENALEX,
                f"Network error reaching OpenAlex: {exc.reason}",
            ) from exc
        except TimeoutError as exc:
            raise LiteratureSourceError(
                ExternalSource.OPENALEX,
                "OpenAlex request timed out.",
            ) from exc
