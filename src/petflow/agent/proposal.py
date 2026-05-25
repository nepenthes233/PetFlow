from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from petflow.domain.enums import EdgeType, NodeStatus, NodeType, RepeatType
from petflow.domain.exceptions import GraphValidationError


@dataclass(slots=True)
class AgentProposalValidator:
    max_nodes: int = 12
    _ENUM_ALIASES: ClassVar[dict[type, dict[str, str]]] = {
        NodeStatus: {
            "pending": NodeStatus.TODO.value,
            "not_started": NodeStatus.TODO.value,
            "in_progress": NodeStatus.DOING.value,
            "active": NodeStatus.DOING.value,
            "complete": NodeStatus.DONE.value,
            "completed": NodeStatus.DONE.value,
            "on_hold": NodeStatus.PAUSED.value,
        },
        NodeType: {
            "milestone": NodeType.CHECKPOINT.value,
            "reference": NodeType.RESOURCE.value,
        },
        EdgeType: {
            "main": EdgeType.DEPENDENCY.value,
            "prerequisite": EdgeType.DEPENDENCY.value,
            "reference": EdgeType.RECOMMENDATION.value,
        },
        RepeatType: {
            "no_repeat": RepeatType.NONE.value,
            "once": RepeatType.NONE.value,
        },
    }
    _PRIORITY_ALIASES: ClassVar[dict[str, int]] = {
        "lowest": 1,
        "low": 2,
        "medium": 3,
        "normal": 3,
        "high": 4,
        "highest": 5,
        "urgent": 5,
        "critical": 5,
    }

    def validate(self, proposal: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(proposal, dict):
            raise GraphValidationError("Agent proposal must be a JSON object.")
        nodes = proposal.get("nodes", [])
        edges = proposal.get("edges", [])
        if not isinstance(nodes, list):
            raise GraphValidationError("Agent proposal nodes must be a list.")
        if not isinstance(edges, list):
            raise GraphValidationError("Agent proposal edges must be a list.")
        if len(nodes) > self.max_nodes:
            raise GraphValidationError(
                f"Agent proposal cannot contain more than {self.max_nodes} nodes."
            )

        normalized_nodes = [
            self._validate_node(node, index) for index, node in enumerate(nodes)
        ]
        self._validate_unique_node_ids(normalized_nodes)
        known_ids = {str(node["id"]) for node in normalized_nodes}
        normalized_edges = [
            self._validate_edge(edge, index, known_ids) for index, edge in enumerate(edges)
        ]
        return {"nodes": normalized_nodes, "edges": normalized_edges}

    @staticmethod
    def _validate_unique_node_ids(nodes: list[dict[str, Any]]) -> None:
        seen: set[str] = set()
        for node in nodes:
            node_id = str(node["id"])
            if node_id in seen:
                raise GraphValidationError(f"Duplicate agent proposal node id: {node_id}")
            seen.add(node_id)

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
        repeat_type = self._coerce_enum(
            RepeatType, node.get("repeat_type"), RepeatType.NONE
        )
        priority = self._normalize_priority(node.get("priority", 3))
        estimated_minutes = self._normalize_integer(
            node.get("estimated_minutes", 30),
            default=30,
            field="estimated_minutes",
        )
        repeat_interval = self._normalize_integer(
            node.get("repeat_interval", 1),
            default=1,
            field="repeat_interval",
        )
        if priority < 1 or priority > 5:
            raise GraphValidationError(
                "Agent proposal node priority must be between 1 and 5."
            )
        if estimated_minutes < 0:
            raise GraphValidationError(
                "Agent proposal node estimate cannot be negative."
            )
        if repeat_interval < 1:
            raise GraphValidationError(
                "Agent proposal node repeat interval must be at least 1."
            )
        return {
            "id": str(node.get("id", f"proposal_node_{index + 1}")),
            "title": title,
            "description": str(node.get("description", "")).strip(),
            "type": node_type.value,
            "status": status.value,
            "priority": priority,
            "estimated_minutes": estimated_minutes,
            "repeat_type": repeat_type.value,
            "repeat_interval": repeat_interval,
            "next_due_at": self._normalize_due_at(node.get("next_due_at")),
            "x": self._normalize_float(
                node.get("x", 100.0 + index * 210.0),
                default=100.0 + index * 210.0,
                field="x",
            ),
            "y": self._normalize_float(
                node.get("y", 120.0), default=120.0, field="y"
            ),
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

    def _coerce_enum(self, enum_cls: type, value: object, default: object) -> object:
        if value is None:
            return default
        if isinstance(value, enum_cls):
            return value
        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        normalized = self._ENUM_ALIASES.get(enum_cls, {}).get(normalized, normalized)
        try:
            return enum_cls(normalized)
        except ValueError as exc:
            raise GraphValidationError(f"Invalid enum value: {value}") from exc

    def _normalize_priority(self, value: object) -> int:
        if value is None:
            return 3
        normalized = str(value).strip().lower()
        if normalized in self._PRIORITY_ALIASES:
            return self._PRIORITY_ALIASES[normalized]
        return self._normalize_integer(value, default=3, field="priority")

    @staticmethod
    def _normalize_integer(value: object, default: int, field: str) -> int:
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise GraphValidationError(
                f"Agent proposal node {field} must be a number."
            ) from exc

    @staticmethod
    def _normalize_float(value: object, default: float, field: str) -> float:
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise GraphValidationError(
                f"Agent proposal node {field} must be a number."
            ) from exc

    @staticmethod
    def _normalize_due_at(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        try:
            datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError as exc:
            raise GraphValidationError(
                "Agent proposal node next_due_at must be an ISO date or datetime."
            ) from exc
        return normalized
