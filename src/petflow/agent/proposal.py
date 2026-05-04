from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from petflow.domain.enums import EdgeType, NodeStatus, NodeType
from petflow.domain.exceptions import GraphValidationError


@dataclass(slots=True)
class AgentProposalValidator:
    def validate(self, proposal: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(proposal, dict):
            raise GraphValidationError("Agent proposal must be a JSON object.")
        nodes = proposal.get("nodes", [])
        edges = proposal.get("edges", [])
        if not isinstance(nodes, list):
            raise GraphValidationError("Agent proposal nodes must be a list.")
        if not isinstance(edges, list):
            raise GraphValidationError("Agent proposal edges must be a list.")

        normalized_nodes = [
            self._validate_node(node, index) for index, node in enumerate(nodes)
        ]
        known_ids = {str(node["id"]) for node in normalized_nodes}
        normalized_edges = [
            self._validate_edge(edge, index, known_ids) for index, edge in enumerate(edges)
        ]
        return {"nodes": normalized_nodes, "edges": normalized_edges}

    def _validate_node(self, node: object, index: int) -> dict[str, Any]:
        if not isinstance(node, dict):
            raise GraphValidationError(
                f"Agent proposal node #{index + 1} must be an object."
            )
        title = str(node.get("title", "")).strip()
        if not title:
            raise GraphValidationError(
                f"Agent proposal node #{index + 1} missing title."
            )
        node_type = self._coerce_enum(NodeType, node.get("type"), NodeType.TASK)
        status = self._coerce_enum(NodeStatus, node.get("status"), NodeStatus.TODO)
        priority = int(node.get("priority", 3))
        estimated_minutes = int(node.get("estimated_minutes", 30))
        if priority < 1 or priority > 5:
            raise GraphValidationError(
                "Agent proposal node priority must be between 1 and 5."
            )
        if estimated_minutes < 0:
            raise GraphValidationError(
                "Agent proposal node estimate cannot be negative."
            )
        return {
            "id": str(node.get("id", f"proposal_node_{index + 1}")),
            "title": title,
            "description": str(node.get("description", "")).strip(),
            "type": node_type.value,
            "status": status.value,
            "priority": priority,
            "estimated_minutes": estimated_minutes,
            "x": float(node.get("x", 100.0 + index * 210.0)),
            "y": float(node.get("y", 120.0)),
        }

    def _validate_edge(
        self,
        edge: object,
        index: int,
        known_ids: set[str],
    ) -> dict[str, Any]:
        if not isinstance(edge, dict):
            raise GraphValidationError(
                f"Agent proposal edge #{index + 1} must be an object."
            )
        source = str(edge.get("source", "")).strip()
        target = str(edge.get("target", "")).strip()
        if not source or not target:
            raise GraphValidationError(
                f"Agent proposal edge #{index + 1} missing source or target."
            )
        if known_ids and (source not in known_ids or target not in known_ids):
            raise GraphValidationError(
                f"Agent proposal edge #{index + 1} references unknown node."
            )
        edge_type = self._coerce_enum(EdgeType, edge.get("type"), EdgeType.DEPENDENCY)
        return {
            "source": source,
            "target": target,
            "type": edge_type.value,
            "label": str(edge.get("label", "")).strip(),
        }

    @staticmethod
    def _coerce_enum(enum_cls: type, value: object, default: object) -> object:
        if value is None:
            return default
        if isinstance(value, enum_cls):
            return value
        try:
            return enum_cls(str(value))
        except ValueError as exc:
            raise GraphValidationError(f"Invalid enum value: {value}") from exc
