from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from petflow.domain.entities import (
    Edge,
    Node,
    PetState,
    ProjectMetadata,
    WorkspaceState,
)
from petflow.domain.enums import EdgeType
from petflow.domain.exceptions import (
    DependencyCycleError,
    GraphValidationError,
)
from petflow.domain.rules import dependency_cycle_would_form


@dataclass(slots=True)
class GraphModel:
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)
    pet: PetState = field(default_factory=PetState)
    workspace: WorkspaceState = field(default_factory=WorkspaceState)
    history: list[dict[str, Any]] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        if node.id in self.nodes:
            raise GraphValidationError(f"Duplicate node id: {node.id}")
        if node.parent_id is not None and node.parent_id not in self.nodes:
            raise GraphValidationError(f"Missing parent node: {node.parent_id}")
        self.nodes[node.id] = node
        node.touch()

    def update_node(self, node_id: str, **changes: Any) -> Node:
        node = self._require_node(node_id)
        for key, value in changes.items():
            if not hasattr(node, key):
                raise GraphValidationError(f"Unknown node field: {key}")
            setattr(node, key, value)
        node.touch()
        return node

    def remove_node(self, node_id: str) -> None:
        self._require_node(node_id)
        self.nodes.pop(node_id)
        for edge_id in list(self.edges):
            edge = self.edges[edge_id]
            if edge.source == node_id or edge.target == node_id:
                self.edges.pop(edge_id)

    def add_edge(self, edge: Edge) -> None:
        if edge.id in self.edges:
            raise GraphValidationError(f"Duplicate edge id: {edge.id}")
        self._require_node(edge.source)
        self._require_node(edge.target)
        if edge.type == EdgeType.DEPENDENCY and dependency_cycle_would_form(
            self.edges, edge.source, edge.target
        ):
            raise DependencyCycleError(
                f"Dependency edge would form cycle: {edge.source} -> {edge.target}"
            )
        self.edges[edge.id] = edge

    def update_edge(self, edge_id: str, **changes: Any) -> Edge:
        edge = self._require_edge(edge_id)
        source = changes.get("source", edge.source)
        target = changes.get("target", edge.target)
        edge_type = changes.get("type", edge.type)
        if "id" in changes:
            raise GraphValidationError("Edge id is immutable")
        self._require_node(source)
        self._require_node(target)
        if edge_type == EdgeType.DEPENDENCY and dependency_cycle_would_form(
            {key: value for key, value in self.edges.items() if key != edge_id},
            source,
            target,
        ):
            raise DependencyCycleError(
                f"Dependency edge would form cycle: {source} -> {target}"
            )
        for key, value in changes.items():
            if not hasattr(edge, key):
                raise GraphValidationError(f"Unknown edge field: {key}")
            setattr(edge, key, value)
        return edge

    def remove_edge(self, edge_id: str) -> None:
        self._require_edge(edge_id)
        self.edges.pop(edge_id)

    def get_node(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Edge | None:
        return self.edges.get(edge_id)

    def incoming_edges(
        self, node_id: str, edge_types: Iterable[EdgeType] | None = None
    ) -> list[Edge]:
        return [
            edge
            for edge in self.edges.values()
            if edge.target == node_id and self._edge_type_matches(edge, edge_types)
        ]

    def outgoing_edges(
        self, node_id: str, edge_types: Iterable[EdgeType] | None = None
    ) -> list[Edge]:
        return [
            edge
            for edge in self.edges.values()
            if edge.source == node_id and self._edge_type_matches(edge, edge_types)
        ]

    def predecessors(
        self, node_id: str, edge_types: Iterable[EdgeType] | None = None
    ) -> list[Node]:
        return [
            self.nodes[edge.source]
            for edge in self.incoming_edges(node_id, edge_types)
            if edge.source in self.nodes
        ]

    def successors(
        self, node_id: str, edge_types: Iterable[EdgeType] | None = None
    ) -> list[Node]:
        return [
            self.nodes[edge.target]
            for edge in self.outgoing_edges(node_id, edge_types)
            if edge.target in self.nodes
        ]

    def record_history(self, action: str, payload: dict[str, Any]) -> None:
        self.history.append(
            {
                "action": action,
                "payload": payload,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "metadata": self.metadata.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "pet": self.pet.to_dict(),
            "workspace": self.workspace.to_dict(),
            "history": list(self.history),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphModel":
        model = cls()
        metadata = data.get("metadata")
        if metadata:
            model.metadata = ProjectMetadata.from_dict(metadata)
        elif "project_name" in data:
            model.metadata.name = data.get("project_name", "PetFlow")

        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            model.nodes[node.id] = node
        for edge_data in data.get("edges", []):
            edge = Edge.from_dict(edge_data)
            model.edges[edge.id] = edge

        pet_data = data.get("pet")
        if pet_data:
            model.pet = PetState.from_dict(pet_data)
        workspace_data = data.get("workspace")
        if workspace_data:
            model.workspace = WorkspaceState.from_dict(workspace_data)
        elif "ui_state" in data:
            model.workspace = WorkspaceState.from_dict(data.get("ui_state", {}))

        model.history = list(data.get("history", []))
        return model

    def _require_node(self, node_id: str) -> Node:
        node = self.nodes.get(node_id)
        if node is None:
            raise GraphValidationError(f"Missing node: {node_id}")
        return node

    def _require_edge(self, edge_id: str) -> Edge:
        edge = self.edges.get(edge_id)
        if edge is None:
            raise GraphValidationError(f"Missing edge: {edge_id}")
        return edge

    @staticmethod
    def _edge_type_matches(
        edge: Edge, edge_types: Iterable[EdgeType] | None
    ) -> bool:
        if edge_types is None:
            return True
        return edge.type in set(edge_types)

