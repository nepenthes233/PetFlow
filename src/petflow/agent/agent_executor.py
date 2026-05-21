from __future__ import annotations

from typing import Any

from petflow.app.graph_service import GraphService
from petflow.agent.proposal import AgentProposalValidator
from petflow.domain.entities import Node
from petflow.domain.enums import EdgeType, NodeStatus, NodeType
from petflow.domain.exceptions import GraphValidationError


class AgentExecutor:
    def __init__(
        self,
        graph_service: GraphService,
        validator: AgentProposalValidator | None = None,
    ) -> None:
        self.graph_service = graph_service
        self.validator = validator or AgentProposalValidator()

    def apply_graph_proposal(
        self,
        proposal: dict[str, Any],
        parent_node_id: str | None = None,
    ) -> list[Node]:
        proposal = self.validator.validate(proposal)
        if (
            parent_node_id is not None
            and self.graph_service.graph.get_node(parent_node_id) is None
        ):
            raise GraphValidationError(f"Missing parent node: {parent_node_id}")
        id_map: dict[str, str] = {}
        created_nodes: list[Node] = []
        for node_data in proposal.get("nodes", []):
            node = self.graph_service.create_node(
                title=str(node_data["title"]),
                description=str(node_data.get("description", "")),
                node_type=NodeType(node_data.get("type", NodeType.TASK.value)),
                status=NodeStatus(node_data.get("status", NodeStatus.TODO.value)),
                priority=int(node_data.get("priority", 3)),
                estimated_minutes=int(node_data.get("estimated_minutes", 30)),
                x=float(node_data.get("x", 100.0)),
                y=float(node_data.get("y", 100.0)),
            )
            id_map[node_data.get("id", node.id)] = node.id
            created_nodes.append(node)

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
        if parent_node_id is not None:
            for node in created_nodes:
                self.graph_service.create_edge(
                    parent_node_id,
                    node.id,
                    EdgeType.RECOMMENDATION,
                    label="agent split",
                )
        return created_nodes
