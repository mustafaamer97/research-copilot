"""Literature layer public API."""
from literature.deduplication import (
    DeduplicatedLiteratureCollection,
    DuplicateGroup,
    LiteratureDeduplicator,
)
from literature.orchestrator import (
    LiteratureSearchCollection,
    LiteratureSearchOrchestrator,
    SourceFailure,
)

__all__ = [
    "DeduplicatedLiteratureCollection",
    "DuplicateGroup",
    "LiteratureDeduplicator",
    "LiteratureSearchCollection",
    "LiteratureSearchOrchestrator",
    "SourceFailure",
]
