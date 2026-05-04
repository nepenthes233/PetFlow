from __future__ import annotations

from datetime import datetime, timezone

from petflow.app.event_bus import EventBus
from petflow.app.id_generator import IdGenerator
from petflow.domain.entities import Edge, Node
from petflow.domain.enums import EdgeType, EventType, NodeStatus, NodeType, RepeatType
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
        repeat_type: RepeatType = RepeatType.NONE,
        next_due_at: str | None = None,
        streak: int = 0,
    ) -> Node:
        self._validate_node_input(title, priority, estimated_minutes, streak)
        node = Node(
            id=self.id_generator.node_id(),
            type=node_type,
            title=title.strip(),
            description=description.strip(),
            status=status,
            priority=priority,
            estimated_minutes=estimated_minutes,
            x=x,
            y=y,
            repeat_type=repeat_type,
            next_due_at=next_due_at,
            streak=streak,
        )
        self.graph.add_node(node)
        self._publish(EventType.NODE_ADDED, {"node_id": node.id})
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
        streak = int(changes.get("streak", current.streak))
        self._validate_node_input(title, priority, estimated_minutes, streak)
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
        repeat_type: RepeatType | None = None,
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
        if next_due_at is not None:
            changes["next_due_at"] = next_due_at
        if streak is not None:
            changes["streak"] = streak
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
                next_due = next_due_at(
                    completed_at,
                    current.repeat_type,
                    current.repeat_interval,
                )
                changes["next_due_at"] = next_due.isoformat() if next_due else None
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
        title: str, priority: int, estimated_minutes: int, streak: int = 0
    ) -> None:
        if not title.strip():
            raise GraphValidationError("Node title cannot be empty.")
        if priority < 1 or priority > 5:
            raise GraphValidationError("Node priority must be between 1 and 5.")
        if estimated_minutes < 0:
            raise GraphValidationError("Estimated minutes cannot be negative.")
        if streak < 0:
            raise GraphValidationError("Routine streak cannot be negative.")

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
    def _coerce_repeat_type(value: object) -> RepeatType:
        if isinstance(value, RepeatType):
            return value
        try:
            return RepeatType(str(value))
        except ValueError as exc:
            raise GraphValidationError(f"Invalid repeat type: {value}") from exc
