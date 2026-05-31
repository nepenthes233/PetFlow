from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from petflow.domain.enums import (
    EdgeType,
    NodeStatus,
    NodeType,
    RepeatType,
    ResourceType,
)
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
            self._validate_edge(edge, index, known_ids)
            for index, edge in enumerate(edges)
        ]
        return {
            "nodes": normalized_nodes,
            "edges": normalized_edges,
            "update_nodes": self._validate_update_nodes(proposal),
            "add_edges": self._validate_add_edges(proposal),
            "delete_node_ids": self._validate_delete_node_ids(proposal),
            "delete_all_nodes": self._validate_delete_all_nodes(proposal),
            "delete_query": self._validate_delete_query(proposal),
            "layout": self._validate_layout(proposal),
        }

    @staticmethod
    def _validate_unique_node_ids(nodes: list[dict[str, Any]]) -> None:
        seen: set[str] = set()
        for node in nodes:
            node_id = str(node["id"])
            if node_id in seen:
                raise GraphValidationError(
                    f"Duplicate agent proposal node id: {node_id}"
                )
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
        routine = node.get("routine")
        if not isinstance(routine, dict):
            routine = {}
        resource = node.get("resource")
        if not isinstance(resource, dict):
            resource = {}
        raw_node_type = node.get("type")
        node_type = self._coerce_enum(NodeType, raw_node_type, NodeType.TASK)
        status = self._coerce_enum(NodeStatus, node.get("status"), NodeStatus.TODO)
        repeat_type = self._coerce_enum(
            RepeatType,
            self._first_present(
                node.get("repeat_type"),
                node.get("recurrence"),
                routine.get("repeat_type"),
                routine.get("recurrence"),
            ),
            RepeatType.NONE,
        )
        if raw_node_type is None and repeat_type != RepeatType.NONE:
            node_type = NodeType.ROUTINE
        priority = self._normalize_priority(node.get("priority", 3))
        estimated_minutes = self._normalize_integer(
            node.get("estimated_minutes", 30),
            default=30,
            field="estimated_minutes",
        )
        actual_minutes = self._normalize_integer(
            node.get("actual_minutes", 0),
            default=0,
            field="actual_minutes",
        )
        repeat_interval = self._normalize_integer(
            self._first_present(
                node.get("repeat_interval"),
                node.get("interval"),
                node.get("interval_days"),
                routine.get("repeat_interval"),
                routine.get("interval"),
                routine.get("interval_days"),
            ),
            default=1,
            field="repeat_interval",
        )
        streak = self._normalize_integer(
            self._first_present(node.get("streak"), routine.get("streak")),
            default=0,
            field="streak",
        )
        if priority < 1 or priority > 5:
            raise GraphValidationError(
                "Agent proposal node priority must be between 1 and 5."
            )
        if estimated_minutes < 0:
            raise GraphValidationError(
                "Agent proposal node estimate cannot be negative."
            )
        if actual_minutes < 0:
            raise GraphValidationError(
                "Agent proposal node actual_minutes cannot be negative."
            )
        if repeat_interval < 1:
            raise GraphValidationError(
                "Agent proposal node repeat interval must be at least 1."
            )
        if streak < 0:
            raise GraphValidationError("Agent proposal node streak cannot be negative.")
        resource_type = self._coerce_enum(
            ResourceType,
            self._first_present(node.get("resource_type"), resource.get("type")),
            ResourceType.URL,
        )
        resource_path = self._first_present(
            node.get("resource_path"),
            node.get("url"),
            node.get("file_path"),
            resource.get("path"),
            resource.get("url"),
        )
        next_due_at = self._first_present(
            node.get("next_due_at"),
            node.get("due_at"),
            node.get("due_date"),
            node.get("deadline"),
            routine.get("next_due_at"),
            routine.get("due_at"),
            routine.get("due_date"),
            routine.get("deadline"),
        )
        return {
            "id": str(node.get("id", f"proposal_node_{index + 1}")),
            "title": title,
            "description": str(node.get("description", "")).strip(),
            "type": node_type.value,
            "status": status.value,
            "priority": priority,
            "estimated_minutes": estimated_minutes,
            "actual_minutes": actual_minutes,
            "tags": self._normalize_string_list(node.get("tags", [])),
            "resource_type": resource_type.value,
            "resource_path": str(resource_path or "").strip(),
            "checklist": self._normalize_checklist(node.get("checklist", [])),
            "repeat_type": repeat_type.value,
            "repeat_interval": repeat_interval,
            "next_due_at": self._normalize_due_at(next_due_at),
            "streak": streak,
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

    def _validate_update_nodes(self, proposal: dict[str, Any]) -> list[dict[str, Any]]:
        raw = proposal.get("update_nodes", proposal.get("node_updates", []))
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise GraphValidationError("Agent proposal update_nodes must be a list.")
        return [
            self._validate_update_node(item, index)
            for index, item in enumerate(raw)
        ]

    def _validate_update_node(self, item: object, index: int) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise GraphValidationError(
                f"Agent proposal update_nodes #{index + 1} must be an object."
            )
        node_id = str(item.get("id", item.get("node_id", ""))).strip()
        query = str(item.get("query", item.get("match", ""))).strip()
        if not node_id and not query:
            raise GraphValidationError(
                f"Agent proposal update_nodes #{index + 1} needs id or query."
            )
        routine = item.get("routine")
        if not isinstance(routine, dict):
            routine = {}
        changes: dict[str, Any] = {}
        if "title" in item or "name" in item:
            title = str(item.get("title", item.get("name", ""))).strip()
            if not title:
                raise GraphValidationError("Agent node update title cannot be empty.")
            changes["title"] = title
        if "description" in item:
            changes["description"] = str(item.get("description", "")).strip()
        if "type" in item:
            changes["type"] = self._coerce_enum(
                NodeType, item.get("type"), NodeType.TASK
            )
        if "status" in item:
            changes["status"] = self._coerce_enum(
                NodeStatus, item.get("status"), NodeStatus.TODO
            )
        if "priority" in item:
            changes["priority"] = self._normalize_priority(item.get("priority"))
        if "estimated_minutes" in item:
            changes["estimated_minutes"] = self._normalize_integer(
                item.get("estimated_minutes"), default=30, field="estimated_minutes"
            )
        if "actual_minutes" in item:
            changes["actual_minutes"] = self._normalize_integer(
                item.get("actual_minutes"), default=0, field="actual_minutes"
            )
        repeat_type = self._first_present(
            item.get("repeat_type"),
            item.get("recurrence"),
            routine.get("repeat_type"),
            routine.get("recurrence"),
        )
        if repeat_type is not None:
            changes["repeat_type"] = self._coerce_enum(
                RepeatType, repeat_type, RepeatType.NONE
            )
        repeat_interval = self._first_present(
            item.get("repeat_interval"),
            item.get("interval"),
            item.get("interval_days"),
            routine.get("repeat_interval"),
            routine.get("interval"),
            routine.get("interval_days"),
        )
        if repeat_interval is not None:
            changes["repeat_interval"] = self._normalize_integer(
                repeat_interval, default=1, field="repeat_interval"
            )
        next_due_at = self._first_present(
            item.get("next_due_at"),
            item.get("due_at"),
            item.get("due_date"),
            item.get("deadline"),
            routine.get("next_due_at"),
            routine.get("due_at"),
            routine.get("due_date"),
            routine.get("deadline"),
        )
        if next_due_at is not None:
            changes["next_due_at"] = self._normalize_due_at(next_due_at)
        if "streak" in item or "streak" in routine:
            changes["streak"] = self._normalize_integer(
                self._first_present(item.get("streak"), routine.get("streak")),
                default=0,
                field="streak",
            )
        if "tags" in item:
            changes["tags"] = self._normalize_string_list(item.get("tags"))
        if "checklist" in item:
            changes["checklist"] = self._normalize_checklist(item.get("checklist"))
        if "resource_type" in item:
            changes["resource_type"] = self._coerce_enum(
                ResourceType, item.get("resource_type"), ResourceType.URL
            )
        if "resource_path" in item:
            changes["resource_path"] = str(item.get("resource_path", "")).strip()
        return {"node_id": node_id, "query": query, "changes": changes}

    def _validate_add_edges(self, proposal: dict[str, Any]) -> list[dict[str, Any]]:
        raw = proposal.get("add_edges", proposal.get("create_edges", []))
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise GraphValidationError("Agent proposal add_edges must be a list.")
        return [self._validate_add_edge(item, index) for index, item in enumerate(raw)]

    def _validate_add_edge(self, item: object, index: int) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise GraphValidationError(
                f"Agent proposal add_edges #{index + 1} must be an object."
            )
        source = str(item.get("source", item.get("source_id", ""))).strip()
        target = str(item.get("target", item.get("target_id", ""))).strip()
        source_query = str(item.get("source_query", "")).strip()
        target_query = str(item.get("target_query", "")).strip()
        if not (source or source_query) or not (target or target_query):
            raise GraphValidationError(
                f"Agent proposal add_edges #{index + 1} needs source and target."
            )
        edge_type = self._coerce_enum(EdgeType, item.get("type"), EdgeType.DEPENDENCY)
        return {
            "source": source,
            "target": target,
            "source_query": source_query,
            "target_query": target_query,
            "type": edge_type.value,
            "label": str(item.get("label", "")).strip(),
        }

    def _validate_delete_node_ids(self, proposal: dict[str, Any]) -> list[str]:
        raw = proposal.get("delete_node_ids", proposal.get("delete_nodes", []))
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise GraphValidationError("Agent proposal delete_node_ids must be a list.")
        node_ids: list[str] = []
        seen: set[str] = set()
        for index, item in enumerate(raw):
            if isinstance(item, dict):
                value = item.get("id", item.get("node_id"))
            else:
                value = item
            node_id = str(value or "").strip()
            if not node_id:
                raise GraphValidationError(
                    f"Agent proposal delete_node_ids #{index + 1} is empty."
                )
            if node_id not in seen:
                node_ids.append(node_id)
                seen.add(node_id)
        return node_ids

    @staticmethod
    def _validate_delete_all_nodes(proposal: dict[str, Any]) -> bool:
        raw = proposal.get("delete_all_nodes", proposal.get("clear_graph", False))
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "all", "clear"}
        if raw is None:
            return False
        raise GraphValidationError("Agent proposal delete_all_nodes must be a boolean.")

    @staticmethod
    def _validate_delete_query(proposal: dict[str, Any]) -> str:
        raw = proposal.get("delete_query", proposal.get("delete_matching", ""))
        if raw is None:
            return ""
        if not isinstance(raw, str):
            raise GraphValidationError("Agent proposal delete_query must be a string.")
        return raw.strip()

    @staticmethod
    def _validate_layout(proposal: dict[str, Any]) -> dict[str, Any]:
        raw = proposal.get("layout", proposal.get("auto_layout", False))
        if raw is None:
            return {"enabled": False, "strategy": "flow"}
        if isinstance(raw, bool):
            return {"enabled": raw, "strategy": "flow"}
        if isinstance(raw, str):
            value = raw.strip().lower()
            enabled = value in {"1", "true", "yes", "auto", "flow", "grid", "layout"}
            strategy = value if value in {"flow", "grid"} else "flow"
            return {"enabled": enabled, "strategy": strategy}
        if isinstance(raw, dict):
            enabled = bool(raw.get("enabled", True))
            strategy = str(raw.get("strategy", "flow")).strip().lower() or "flow"
            if strategy not in {"flow", "grid"}:
                strategy = "flow"
            return {"enabled": enabled, "strategy": strategy}
        raise GraphValidationError("Agent proposal layout must be a boolean or object.")

    @staticmethod
    def _first_present(*values: object) -> object | None:
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    @staticmethod
    def _normalize_string_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw_items = value.split(",")
        elif isinstance(value, list):
            raw_items = value
        else:
            raise GraphValidationError("Agent proposal node tags must be a list.")
        normalized: list[str] = []
        for item in raw_items:
            text = str(item).strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    @staticmethod
    def _normalize_checklist(value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise GraphValidationError("Agent proposal node checklist must be a list.")
        items: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text", item.get("item", item.get("title", "")))
            else:
                text = item
            normalized = str(text).strip()
            if normalized:
                items.append(normalized)
        return items

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
