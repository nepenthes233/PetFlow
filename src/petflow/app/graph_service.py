from __future__ import annotations

from petflow.app.event_bus import EventBus
from petflow.app.id_generator import IdGenerator
from petflow.domain.entities import Edge, Node
from petflow.domain.enums import EdgeType, EventType, NodeStatus, NodeType
from petflow.domain.events import DomainEvent
from petflow.domain.exceptions import GraphValidationError
from petflow.domain.graph import GraphModel


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
    ) -> Node:
        self._validate_node_input(title, priority, estimated_minutes)
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
        )
        self.graph.add_node(node)
        self._publish(EventType.NODE_ADDED, {"node_id": node.id})
        return node

    def update_node(self, node_id: str, **changes: object) -> Node:
        current = self.graph.get_node(node_id)
        if current is None:
            raise GraphValidationError(f"Missing node: {node_id}")
        title = str(changes.get("title", current.title))
        priority = int(changes.get("priority", current.priority))
        estimated_minutes = int(
            changes.get("estimated_minutes", current.estimated_minutes)
        )
        self._validate_node_input(title, priority, estimated_minutes)
        if "title" in changes:
            changes["title"] = title.strip()
        if "description" in changes:
            changes["description"] = str(changes["description"]).strip()
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
    ) -> Node:
        return self.update_node(
            node_id,
            title=title,
            description=description,
            type=node_type,
            status=status,
            priority=priority,
            estimated_minutes=estimated_minutes,
        )

    def update_node_status(self, node_id: str, status: NodeStatus) -> Node:
        node = self.graph.update_node(node_id, status=status)
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
        edge_type: EdgeType = EdgeType.DEPENDENCY,
    ) -> Edge:
        edge = Edge(
            id=self.id_generator.edge_id(),
            source=source,
            target=target,
            type=edge_type,
        )
        self.graph.add_edge(edge)
        self._publish(EventType.EDGE_ADDED, {"edge_id": edge.id})
        return edge

    def delete_edge(self, edge_id: str) -> None:
        self.graph.remove_edge(edge_id)
        self._publish(EventType.EDGE_REMOVED, {"edge_id": edge_id})

    def update_edge(self, edge_id: str, **changes: object) -> Edge:
        if "type" in changes and not isinstance(changes["type"], EdgeType):
            changes["type"] = EdgeType(str(changes["type"]))
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
        title: str, priority: int, estimated_minutes: int
    ) -> None:
        if not title.strip():
            raise GraphValidationError("Node title cannot be empty.")
        if priority < 1 or priority > 5:
            raise GraphValidationError("Node priority must be between 1 and 5.")
        if estimated_minutes < 0:
            raise GraphValidationError("Estimated minutes cannot be negative.")
