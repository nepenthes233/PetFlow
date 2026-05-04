from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt

from petflow.app.graph_service import GraphService
from petflow.domain.graph import GraphModel


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

    def apply_grid_layout(self, graph_service: GraphService) -> None:
        for node_id, (x, y) in self.grid_positions(graph_service.graph).items():
            graph_service.move_node(node_id, x, y)
