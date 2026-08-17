"""Literature search orchestrator — provider-agnostic multi-source search."""
from __future__ import annotations

from dataclasses import dataclass, field

from domain.literature_search import LiteratureSearchStrategy
from services.literature_source import (
    LiteratureSearchResult,
    LiteratureSourceAdapter,
    LiteratureSourceError,
)


@dataclass(frozen=True)
class SourceFailure:
    """Records a failed adapter execution without discarding successful results."""
    adapter_name: str
    error: LiteratureSourceError


@dataclass
class LiteratureSearchCollection:
    """
    Aggregated results from all executed adapters.

    Preserves source order, empty results, and partial failures.
    Never deduplicates.
    """
    results: list[LiteratureSearchResult] = field(default_factory=list)
    failures: list[SourceFailure] = field(default_factory=list)

    @property
    def all_records(self):
        """Flat list of all LiteratureRecord objects across all results."""
        records = []
        for result in self.results:
            records.extend(result.records)
        return records

    @property
    def total_records(self) -> int:
        return sum(len(r.records) for r in self.results)

    @property
    def has_failures(self) -> bool:
        return len(self.failures) > 0


class LiteratureSearchOrchestrator:
    """
    Coordinates multiple LiteratureSourceAdapters against a single strategy.

    - Executes adapters in injection order.
    - Does not mutate the strategy.
    - Does not deduplicate records.
    - Does not retry on failure.
    - Does not run concurrently.
    - Preserves successful results when an adapter fails.
    """

    def __init__(self, adapters: list[LiteratureSourceAdapter]) -> None:
        self._adapters = list(adapters)

    def search(
        self, strategy: LiteratureSearchStrategy
    ) -> LiteratureSearchCollection:
        """
        Execute every injected adapter with the exact same strategy.

        Returns a LiteratureSearchCollection preserving:
        - all successful LiteratureSearchResult objects (in adapter order)
        - all SourceFailure objects for adapters that raised LiteratureSourceError
        """
        collection = LiteratureSearchCollection()

        for adapter in self._adapters:
            try:
                result = adapter.search(strategy)
                collection.results.append(result)
            except LiteratureSourceError as exc:
                collection.failures.append(
                    SourceFailure(
                        adapter_name=type(adapter).__name__,
                        error=exc,
                    )
                )

        return collection
