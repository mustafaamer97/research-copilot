"""Crossref source adapter — official REST API implementation."""
from __future__ import annotations

import json
import re
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

_SEARCH_URL = "https://api.crossref.org/works"
_DEFAULT_MAX_RESULTS = 100
_DEFAULT_TIMEOUT = 30
_USER_AGENT = "ResearchCopilot/1.0 (https://github.com/research-copilot)"

# Deterministic JATS/XML tag stripper — no AI, no semantic rewriting
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_markup(text: str) -> str:
    """Remove XML/JATS tags deterministically. Preserves all text content."""
    return _TAG_RE.sub("", text).strip()


class CrossrefAdapter(LiteratureSourceAdapter):
    """
    Retrieves real scholarly metadata via the official Crossref REST API.

    Never invents records.
    Never modifies the supplied search strategy.
    All HTTP is bounded by timeout and result limit.
    """

    def __init__(
        self,
        max_results: int = _DEFAULT_MAX_RESULTS,
        timeout: int = _DEFAULT_TIMEOUT,
        mailto: str | None = None,
    ) -> None:
        self._max_results = max_results
        self._timeout = timeout
        self._mailto = mailto

    # ------------------------------------------------------------------
    # Public contract
    # ------------------------------------------------------------------

    def search(self, strategy: LiteratureSearchStrategy) -> LiteratureSearchResult:
        retrieved_at = datetime.now(timezone.utc)
        query = strategy.boolean_query or ""

        raw_items = self._query_api(query)

        records: list[LiteratureRecord] = []
        for item in raw_items:
            record = self._map_item(item, retrieved_at)
            if record is not None:
                records.append(record)

        return LiteratureSearchResult(
            source=ExternalSource.CROSSREF,
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
            "rows": str(self._max_results),
        }
        if self._mailto:
            params["mailto"] = self._mailto

        url = f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}"

        try:
            raw = self._get(url)
        except LiteratureSourceError:
            raise
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.CROSSREF,
                f"Crossref request failed: {exc}",
            ) from exc

        try:
            data = json.loads(raw)
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.CROSSREF,
                f"Crossref response could not be parsed as JSON: {exc}",
            ) from exc

        try:
            message = data.get("message")
            if message is None:
                raise LiteratureSourceError(
                    ExternalSource.CROSSREF,
                    "Crossref response missing expected 'message' field.",
                )
            if not isinstance(message, dict):
                raise LiteratureSourceError(
                    ExternalSource.CROSSREF,
                    "Crossref 'message' field is not an object.",
                )
            items = message.get("items")
            if items is None:
                raise LiteratureSourceError(
                    ExternalSource.CROSSREF,
                    "Crossref response missing expected 'items' field.",
                )
            if not isinstance(items, list):
                raise LiteratureSourceError(
                    ExternalSource.CROSSREF,
                    "Crossref 'items' field is not a list.",
                )
            return items
        except LiteratureSourceError:
            raise
        except Exception as exc:
            raise LiteratureSourceError(
                ExternalSource.CROSSREF,
                f"Crossref response structure unexpected: {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # Item mapping
    # ------------------------------------------------------------------

    def _map_item(
        self, item: dict, retrieved_at: datetime
    ) -> LiteratureRecord | None:
        # DOI — canonical Crossref identifier
        doi_raw = str(item.get("DOI") or "").strip()
        doi: str | None = doi_raw if doi_raw else None

        # source_record_id — use DOI when available, else URL, else fail
        source_record_id: str = ""
        if doi:
            source_record_id = doi
        else:
            url_raw = str(item.get("URL") or "").strip()
            if url_raw:
                source_record_id = url_raw

        if not source_record_id:
            raise LiteratureSourceError(
                ExternalSource.CROSSREF,
                "Crossref item has no usable identifier (no DOI or URL).",
            )

        # Title — required; Crossref provides as list
        title_list = item.get("title") or []
        title: str = ""
        if isinstance(title_list, list) and title_list:
            title = str(title_list[0]).strip()
        elif isinstance(title_list, str):
            title = title_list.strip()

        if not title:
            raise LiteratureSourceError(
                ExternalSource.CROSSREF,
                f"Crossref item {source_record_id} has no valid title.",
            )

        # Authors
        authors = self._extract_authors(item)

        # Journal — container-title is a list
        journal: str | None = None
        container = item.get("container-title") or []
        if isinstance(container, list) and container:
            val = str(container[0]).strip()
            journal = val if val else None
        elif isinstance(container, str) and container.strip():
            journal = container.strip()

        # Publication date
        pub_date: str | None = self._extract_pub_date(item)

        # Abstract — strip JATS markup deterministically
        abstract_raw = item.get("abstract") or None
        abstract: str | None = None
        if isinstance(abstract_raw, str) and abstract_raw.strip():
            cleaned = _strip_markup(abstract_raw)
            abstract = cleaned if cleaned else None

        # Source URL
        source_url: str | None = None
        if doi:
            source_url = f"https://doi.org/{doi}"
        else:
            url_field = str(item.get("URL") or "").strip()
            source_url = url_field if url_field else None

        # PMID — Crossref rarely supplies this; only use if explicitly present
        pmid: str | None = None

        return LiteratureRecord(
            title=title,
            authors=authors,
            journal=journal,
            publication_date=pub_date,
            abstract=abstract,
            doi=doi,
            pmid=pmid,
            source=ExternalSource.CROSSREF,
            source_record_id=source_record_id,
            source_url=source_url,
            retrieved_at=retrieved_at,
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_authors(self, item: dict) -> list[str]:
        authors: list[str] = []
        for author in item.get("author") or []:
            if not isinstance(author, dict):
                continue
            given = str(author.get("given") or "").strip()
            family = str(author.get("family") or "").strip()
            name_raw = str(author.get("name") or "").strip()

            if family and given:
                authors.append(f"{family} {given}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)
            elif name_raw:
                authors.append(name_raw)
            # If none present: skip — do not invent
        return authors

    def _extract_pub_date(self, item: dict) -> str | None:
        # Prefer published-print, then published-online, then issued
        for key in ("published-print", "published-online", "issued"):
            date_obj = item.get(key)
            if not isinstance(date_obj, dict):
                continue
            date_parts = date_obj.get("date-parts")
            if not isinstance(date_parts, list) or not date_parts:
                continue
            parts = date_parts[0]
            if not isinstance(parts, list) or not parts:
                continue
            # Filter None values
            valid_parts = [str(p) for p in parts if p is not None]
            if valid_parts:
                return "-".join(valid_parts)
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
                ExternalSource.CROSSREF,
                f"HTTP {exc.code} from Crossref: {exc.reason}",
            ) from exc
        except urllib.error.URLError as exc:
            raise LiteratureSourceError(
                ExternalSource.CROSSREF,
                f"Network error reaching Crossref: {exc.reason}",
            ) from exc
        except TimeoutError as exc:
            raise LiteratureSourceError(
                ExternalSource.CROSSREF,
                "Crossref request timed out.",
            ) from exc
