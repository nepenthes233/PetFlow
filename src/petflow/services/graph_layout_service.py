from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt
from typing import TYPE_CHECKING

from petflow.domain.graph import GraphModel

if TYPE_CHECKING:
    from petflow.app.graph_service import GraphService


@dataclass(slots=True)
class GraphLayoutService:
    start_x: float = 120.0
    start_y: float = 120.0
    column_gap: float = 240.0
    row_gap: float = 140.0

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
        for node_id, (x, y) in self.grid_positions(graph_service.graph).items():
            graph_service.move_node(node_id, x, y)

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
