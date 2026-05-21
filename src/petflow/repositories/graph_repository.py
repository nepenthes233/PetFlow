from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from petflow.domain.exceptions import RepositoryError
from petflow.domain.graph import GraphModel


class GraphRepository(ABC):
    @abstractmethod
    def load(self, path: str | Path) -> GraphModel:
        raise NotImplementedError

    @abstractmethod
    def save(self, graph: GraphModel, path: str | Path) -> None:
        raise NotImplementedError


class JsonGraphRepository(GraphRepository):
    def load(self, path: str | Path) -> GraphModel:
        file_path = Path(path)
        if not file_path.exists():
            return GraphModel()
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RepositoryError(f"Failed to load graph: {file_path}") from exc
        return GraphModel.from_dict(data)

    def save(self, graph: GraphModel, path: str | Path) -> None:
        file_path = Path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                json.dumps(graph.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise RepositoryError(f"Failed to save graph: {file_path}") from exc
