"""Serialization utilities and in-memory project repository."""
import copy
import json
from uuid import UUID

from domain.project import ResearchProject


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def serialize_project(project: ResearchProject) -> str:
    """Serialize a ResearchProject to a JSON string."""
    return project.model_dump_json()


def deserialize_project(data: str) -> ResearchProject:
    """Restore a ResearchProject from a JSON string.

    Raises ValidationError if the data is invalid.
    """
    return ResearchProject.model_validate_json(data)


# ---------------------------------------------------------------------------
# In-memory repository
# ---------------------------------------------------------------------------

class InMemoryProjectRepository:
    """Thread-unsafe in-memory store for ResearchProject instances."""

    def __init__(self) -> None:
        self._store: dict[UUID, str] = {}

    def save(self, project: ResearchProject) -> None:
        """Persist (or replace) a project by its id."""
        self._store[project.id] = serialize_project(project)

    def get(self, project_id: UUID) -> ResearchProject | None:
        """Return a deserialized copy of the project, or None if not found."""
        raw = self._store.get(project_id)
        if raw is None:
            return None
        return deserialize_project(raw)

    def delete(self, project_id: UUID) -> None:
        """Remove a project; silently does nothing if absent."""
        self._store.pop(project_id, None)

    def exists(self, project_id: UUID) -> bool:
        """Return True if a project with the given id is stored."""
        return project_id in self._store
