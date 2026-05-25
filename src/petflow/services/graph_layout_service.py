from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt
from typing import TYPE_CHECKING

from petflow.domain.graph import GraphModel
from petflow.domain.enums import EdgeType, NodeType

if TYPE_CHECKING:
    from petflow.app.graph_service import GraphService


@dataclass(slots=True)
class GraphLayoutService:
    start_x: float = 120.0
    start_y: float = 120.0
    column_gap: float = 270.0
    row_gap: float = 170.0

    def grid_positions(self, graph: GraphModel) -> dict[str, tuple[float, float]]:
        node_ids = list(graph.nodes)
        if not node_ids:
            return {}
        columns = max(1, ceil(sqrt(len(node_ids))))
        positions: dict[str, tuple[float, float]] = {}
        for index, node_id in enumerate(node_ids):
            row = index // columns
            column = index % columns
            positions[node_id] = (
                self.start_x + column * self.column_gap,
                self.start_y + row * self.row_gap,
            )
        return positions

    def apply_grid_layout(self, graph_service: "GraphService") -> None:
        for node_id, (x, y) in self.flow_positions(graph_service.graph).items():
            graph_service.move_node(node_id, x, y)

    def flow_positions(self, graph: GraphModel) -> dict[str, tuple[float, float]]:
        primary = [
            node
            for node in graph.nodes.values()
            if node.type not in {NodeType.RESOURCE, NodeType.REWARD}
        ]
        resources = [
            node for node in graph.nodes.values() if node.type == NodeType.RESOURCE
        ]
        rewards = [node for node in graph.nodes.values() if node.type == NodeType.REWARD]
        if not primary:
            return self.grid_positions(graph)

        dependency_edges = [
            edge
            for edge in graph.edges.values()
            if edge.type == EdgeType.DEPENDENCY
        ]
        levels: dict[str, int] = {node.id: 0 for node in primary}
        primary_ids = set(levels)
        if dependency_edges:
            for _iteration in range(len(primary)):
                changed = False
                for edge in dependency_edges:
                    if edge.source in primary_ids and edge.target in primary_ids:
                        target_level = levels[edge.source] + 1
                        if target_level > levels[edge.target]:
                            levels[edge.target] = target_level
                            changed = True
                if not changed:
                    break
        else:
            levels = {node.id: index for index, node in enumerate(primary)}

        level_rows: dict[int, int] = {}
        positions: dict[str, tuple[float, float]] = {}
        for node in primary:
            level = levels[node.id]
            row = level_rows.get(level, 0)
            positions[node.id] = (
                self.start_x + level * self.column_gap,
                self.start_y + row * self.row_gap,
            )
            level_rows[level] = row + 1

        max_level = max(levels.values(), default=0)
        resource_y = self.start_y + max(level_rows.values(), default=1) * self.row_gap
        current_id = graph.workspace.current_node_id
        resource_anchor_x = positions.get(current_id, (self.start_x, self.start_y))[0]
        for index, node in enumerate(resources):
            positions[node.id] = (
                resource_anchor_x + index * self.column_gap,
                resource_y,
            )
        for index, node in enumerate(rewards):
            positions[node.id] = (
                self.start_x + (max_level + 1) * self.column_gap,
                self.start_y + index * self.row_gap,
            )
        return positions

    def apply_subset_grid_layout(
        self,
        graph_service: "GraphService",
        node_ids: list[str],
    ) -> None:
        existing_ids = [
            node_id for node_id in node_ids if graph_service.graph.get_node(node_id)
        ]
        if not existing_ids:
            return
        other_nodes = [
            node
            for node_id, node in graph_service.graph.nodes.items()
            if node_id not in set(existing_ids)
        ]
        start_y = self.start_y
        if other_nodes:
            start_y = max(node.y for node in other_nodes) + self.row_gap
        columns = max(1, ceil(sqrt(len(existing_ids))))
        for index, node_id in enumerate(existing_ids):
            row = index // columns
            column = index % columns
            graph_service.move_node(
                node_id,
                self.start_x + column * self.column_gap,
                start_y + row * self.row_gap,
            )
