from __future__ import annotations

from typing import Any

from petflow.app.graph_service import GraphService
from petflow.domain.enums import EdgeType, NodeType


class AgentExecutor:
    def __init__(self, graph_service: GraphService) -> None:
        self.graph_service = graph_service

    def apply_graph_proposal(self, proposal: dict[str, Any]) -> None:
        id_map: dict[str, str] = {}
        for node_data in proposal.get("nodes", []):
            node = self.graph_service.create_node(
                title=node_data.get("title", "Untitled"),
                node_type=NodeType(node_data.get("type", NodeType.TASK.value)),
                x=float(node_data.get("x", 100.0)),
                y=float(node_data.get("y", 100.0)),
            )
            id_map[node_data.get("id", node.id)] = node.id

        for edge_data in proposal.get("edges", []):
            source = id_map.get(edge_data.get("source"), edge_data.get("source"))
            target = id_map.get(edge_data.get("target"), edge_data.get("target"))
            if source and target:
                self.graph_service.create_edge(
                    source=source,
                    target=target,
                    edge_type=EdgeType(
                        edge_data.get("type", EdgeType.DEPENDENCY.value)
                    ),
                    label=edge_data.get("label", ""),
                )
