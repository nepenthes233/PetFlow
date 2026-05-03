from __future__ import annotations

from pathlib import Path

from petflow.domain.graph import GraphModel
from petflow.repositories.graph_repository import GraphRepository, JsonGraphRepository


class StorageService:
    def __init__(self, repository: GraphRepository | None = None) -> None:
        self.repository = repository or JsonGraphRepository()

    def load_graph(self, path: str | Path) -> GraphModel:
        return self.repository.load(path)

    def save_graph(self, graph: GraphModel, path: str | Path) -> None:
        self.repository.save(graph, path)
