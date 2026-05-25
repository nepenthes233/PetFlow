from __future__ import annotations

from datetime import datetime, timezone

from petflow.app.event_bus import EventBus
from petflow.app.id_generator import IdGenerator
from petflow.domain.entities import ChecklistItem, Edge, Node
from petflow.domain.enums import (
    EdgeType,
    EventType,
    NodeStatus,
    NodeType,
    RepeatType,
    ResourceType,
)
from petflow.domain.events import DomainEvent
from petflow.domain.exceptions import GraphValidationError
from petflow.domain.graph import GraphModel
from petflow.domain.routine import next_due_at


class GraphService:
    def __init__(
        self,
        graph: GraphModel,
        event_bus: EventBus | None = None,
        id_generator: IdGenerator | None = None,
    ) -> None:
        self.graph = graph
        self.event_bus = event_bus or EventBus()
        self.id_generator = id_generator or IdGenerator()

    def create_node(
        self,
        title: str,
        node_type: NodeType = NodeType.TASK,
        x: float = 100.0,
        y: float = 100.0,
        description: str = "",
        status: NodeStatus = NodeStatus.TODO,
        priority: int = 3,
        estimated_minutes: int = 30,
        actual_minutes: int = 0,
        tags: list[str] | None = None,
        resource_type: ResourceType | str = ResourceType.URL,
        resource_path: str = "",
        checklist: list[ChecklistItem] | list[str] | None = None,
        repeat_type: RepeatType = RepeatType.NONE,
        repeat_interval: int = 1,
        next_due_at: str | None = None,
        streak: int = 0,
    ) -> Node:
        self._validate_node_input(
            title, priority, estimated_minutes, streak, repeat_interval
        )
        if actual_minutes < 0:
            raise GraphValidationError("Actual minutes cannot be negative.")
        node = Node(
            id=self.id_generator.node_id(),
            type=node_type,
            title=title.strip(),
            description=description.strip(),
            status=status,
            priority=priority,
            estimated_minutes=estimated_minutes,
            actual_minutes=actual_minutes,
            x=x,
            y=y,
            tags=self._normalize_tags(tags or []),
            resource_type=self._coerce_resource_type(resource_type),
            resource_path=resource_path.strip(),
            checklist=self._normalize_checklist(checklist or []),
            repeat_type=repeat_type,
            repeat_interval=repeat_interval,
            next_due_at=next_due_at,
            streak=streak,
        )
        self.graph.add_node(node)
        self._publish(EventType.NODE_ADDED, {"node_id": node.id})
        return node

    def create_resource_node(
        self,
        title: str,
        resource_type: ResourceType | str = ResourceType.TEXT,
        resource_path: str = "",
        description: str = "",
        x: float = 100.0,
        y: float = 100.0,
    ) -> Node:
        resource_type = self._coerce_resource_type(resource_type)
        node = self.create_node(
            title=title,
            node_type=NodeType.RESOURCE,
            description=description,
            priority=2,
            estimated_minutes=0,
            x=x,
            y=y,
        )
        node = self.graph.update_node(
            node.id,
            resource_type=resource_type,
            resource_path=resource_path.strip(),
        )
        self._publish(
            EventType.NODE_UPDATED,
            {"node_id": node.id, "field": "resource"},
        )
        return node

    def add_node_attachment(self, node_id: str, path: str) -> Node:
        current = self.graph.get_node(node_id)
        if current is None:
            raise GraphValidationError(f"Missing node: {node_id}")
        normalized_path = path.strip()
        if not normalized_path:
            raise GraphValidationError("Attachment path cannot be empty.")
        attachments = list(current.attachments)
        if normalized_path not in attachments:
            attachments.append(normalized_path)
        node = self.graph.update_node(node_id, attachments=attachments)
        self._publish(
            EventType.NODE_UPDATED,
            {"node_id": node_id, "field": "attachments"},
        )
        return node

    def update_node(self, node_id: str, **changes: object) -> Node:
        current = self.graph.get_node(node_id)
        if current is None:
            raise GraphValidationError(f"Missing node: {node_id}")
        if "status" in changes:
            raise GraphValidationError(
                "Use update_node_status() to change node status."
            )
        title = str(changes.get("title", current.title))
        priority = int(changes.get("priority", current.priority))
        estimated_minutes = int(
            changes.get("estimated_minutes", current.estimated_minutes)
        )
        actual_minutes = int(changes.get("actual_minutes", current.actual_minutes))
        streak = int(changes.get("streak", current.streak))
        repeat_interval = int(changes.get("repeat_interval", current.repeat_interval))
        self._validate_node_input(
            title, priority, estimated_minutes, streak, repeat_interval
        )
        if actual_minutes < 0:
            raise GraphValidationError("Actual minutes cannot be negative.")
        if "title" in changes:
            changes["title"] = title.strip()
        if "description" in changes:
            changes["description"] = str(changes["description"]).strip()
        if "repeat_type" in changes:
            changes["repeat_type"] = self._coerce_repeat_type(changes["repeat_type"])
        if "next_due_at" in changes:
            next_due_value = changes["next_due_at"]
            changes["next_due_at"] = str(next_due_value).strip() or None
        node = self.graph.update_node(node_id, **changes)
        self._publish(EventType.NODE_UPDATED, {"node_id": node_id, "field": "detail"})
        return node

    def rename_node(self, node_id: str, title: str) -> Node:
        return self.update_node(node_id, title=title)

    def update_node_detail(
        self,
        node_id: str,
        title: str,
        description: str,
        node_type: NodeType,
        status: NodeStatus,
        priority: int,
        estimated_minutes: int,
        actual_minutes: int | None = None,
        tags: list[str] | None = None,
        resource_type: ResourceType | str | None = None,
        resource_path: str | None = None,
        checklist: list[ChecklistItem] | list[str] | None = None,
        repeat_type: RepeatType | None = None,
        repeat_interval: int | None = None,
        next_due_at: str | None = None,
        streak: int | None = None,
    ) -> Node:
        current = self.graph.get_node(node_id)
        if current is None:
            raise GraphValidationError(f"Missing node: {node_id}")
        changes: dict[str, object] = {
            "title": title,
            "description": description,
            "type": node_type,
            "priority": priority,
            "estimated_minutes": estimated_minutes,
        }
        if repeat_type is not None:
            changes["repeat_type"] = repeat_type
        if repeat_interval is not None:
            changes["repeat_interval"] = repeat_interval
        if next_due_at is not None:
            changes["next_due_at"] = next_due_at
        if streak is not None:
            changes["streak"] = streak
        if actual_minutes is not None:
            changes["actual_minutes"] = actual_minutes
        if tags is not None:
            changes["tags"] = self._normalize_tags(tags)
        if resource_type is not None:
            changes["resource_type"] = self._coerce_resource_type(resource_type)
        if resource_path is not None:
            changes["resource_path"] = resource_path.strip()
        if checklist is not None:
            changes["checklist"] = self._normalize_checklist(checklist)
        node = self.update_node(
            node_id,
            **changes,
        )
        if current.status != status:
            node = self.update_node_status(node_id, status)
        return node

    def update_node_status(self, node_id: str, status: NodeStatus) -> Node:
        current = self.graph.get_node(node_id)
        if current is None:
            raise GraphValidationError(f"Missing node: {node_id}")
        previous_status = current.status
        changes: dict[str, object] = {"status": status}
        if status == NodeStatus.DONE:
            completed_at = datetime.now(timezone.utc)
            completed_at_value = completed_at.isoformat()
            changes["completed_at"] = completed_at_value
            if current.type == NodeType.ROUTINE:
                changes["last_completed_at"] = completed_at_value
                changes["streak"] = current.streak + 1
            if current.repeat_type != RepeatType.NONE:
                next_due = next_due_at(
                    completed_at,
                    current.repeat_type,
                    current.repeat_interval,
                )
                changes["next_due_at"] = next_due.isoformat() if next_due else None
                changes["status"] = NodeStatus.TODO
        elif previous_status == NodeStatus.DONE:
            changes["completed_at"] = None

        node = self.graph.update_node(node_id, **changes)
        self.graph.record_history(
            "node.status_changed",
            {
                "node_id": node_id,
                "from": previous_status.value,
                "to": status.value,
            },
        )
        if status == NodeStatus.DONE:
            self.graph.record_history("node.completed", {"node_id": node_id})
        self._publish(
            EventType.NODE_UPDATED,
            {"node_id": node_id, "field": "status", "status": status.value},
        )
        return node

    def move_node(self, node_id: str, x: float, y: float) -> Node:
        node = self.graph.update_node(node_id, x=x, y=y)
        self._publish(EventType.NODE_UPDATED, {"node_id": node_id, "field": "pos"})
        return node

    def delete_node(self, node_id: str) -> None:
        self.graph.remove_node(node_id)
        self._publish(EventType.NODE_REMOVED, {"node_id": node_id})

    def create_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType | str = EdgeType.DEPENDENCY,
        label: object = "",
    ) -> Edge:
        edge_type = self._coerce_edge_type(edge_type)
        label = self._normalize_edge_label(label)
        self._validate_edge_label(label)
        edge = Edge(
            id=self.id_generator.edge_id(),
            source=source,
            target=target,
            type=edge_type,
            label=label,
        )
        self.graph.add_edge(edge)
        self._publish(EventType.EDGE_ADDED, {"edge_id": edge.id})
        return edge

    def delete_edge(self, edge_id: str) -> None:
        self.graph.remove_edge(edge_id)
        self._publish(EventType.EDGE_REMOVED, {"edge_id": edge_id})

    def update_edge(self, edge_id: str, **changes: object) -> Edge:
        if self.graph.get_edge(edge_id) is None:
            raise GraphValidationError(f"Missing edge: {edge_id}")
        if "type" in changes:
            changes["type"] = self._coerce_edge_type(changes["type"])
        if "label" in changes:
            label = self._normalize_edge_label(changes["label"])
            self._validate_edge_label(label)
            changes["label"] = label
        edge = self.graph.update_edge(edge_id, **changes)
        self._publish(EventType.EDGE_UPDATED, {"edge_id": edge_id})
        return edge

    def set_current_node(self, node_id: str | None) -> None:
        if node_id is not None:
            self.graph.get_node(node_id)
        self.graph.workspace.current_node_id = node_id
        self.graph.pet.current_node_id = node_id
        self._publish(EventType.GRAPH_CHANGED, {"current_node_id": node_id})

    def _publish(self, event_type: EventType, payload: dict[str, object]) -> None:
        self.event_bus.publish(
            DomainEvent(type=event_type, source="graph_service", payload=payload)
        )

    @staticmethod
    def _validate_node_input(
        title: str,
        priority: int,
        estimated_minutes: int,
        streak: int = 0,
        repeat_interval: int = 1,
    ) -> None:
        if not title.strip():
            raise GraphValidationError("Node title cannot be empty.")
        if priority < 1 or priority > 5:
            raise GraphValidationError("Node priority must be between 1 and 5.")
        if estimated_minutes < 0:
            raise GraphValidationError("Estimated minutes cannot be negative.")
        if streak < 0:
            raise GraphValidationError("Routine streak cannot be negative.")
        if repeat_interval < 1:
            raise GraphValidationError("Repeat interval must be at least 1.")

    @staticmethod
    def _coerce_edge_type(value: object) -> EdgeType:
        if isinstance(value, EdgeType):
            return value
        try:
            return EdgeType(str(value))
        except ValueError as exc:
            raise GraphValidationError(f"Invalid edge type: {value}") from exc

    @staticmethod
    def _validate_edge_label(label: str) -> None:
        if len(label) > 80:
            raise GraphValidationError("Edge label must be 80 characters or fewer.")

    @staticmethod
    def _normalize_edge_label(label: object) -> str:
        if label is None:
            return ""
        return str(label).strip()

    @staticmethod
    def _normalize_tags(tags: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in tags:
            value = str(tag).strip()
            if value and value not in normalized:
                normalized.append(value)
        return normalized

    @staticmethod
    def _normalize_checklist(
        checklist: list[ChecklistItem] | list[str],
    ) -> list[ChecklistItem]:
        normalized: list[ChecklistItem] = []
        for index, item in enumerate(checklist):
            if isinstance(item, ChecklistItem):
                text = item.text.strip()
                checked = item.checked
                item_id = item.id or f"check_{index + 1}"
            else:
                text = str(item).strip()
                checked = False
                item_id = f"check_{index + 1}"
            if text:
                normalized.append(
                    ChecklistItem(id=item_id, text=text, checked=checked)
                )
        return normalized

    @staticmethod
    def _coerce_repeat_type(value: object) -> RepeatType:
        if isinstance(value, RepeatType):
            return value
        try:
            return RepeatType(str(value))
        except ValueError as exc:
            raise GraphValidationError(f"Invalid repeat type: {value}") from exc

    @staticmethod
    def _coerce_resource_type(value: object) -> ResourceType:
        if isinstance(value, ResourceType):
            return value
        try:
            return ResourceType(str(value))
        except ValueError as exc:
            raise GraphValidationError(f"Invalid resource type: {value}") from exc
