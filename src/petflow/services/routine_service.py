from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from petflow.domain.entities import Node
from petflow.domain.enums import NodeStatus, NodeType
from petflow.domain.graph import GraphModel
from petflow.domain.routine import is_routine_due, parse_iso_datetime


@dataclass(slots=True)
class RoutineService:
    def routine_state(self, node: Node, now: datetime | None = None) -> str:
        if node.type != NodeType.ROUTINE:
            return ""
        if node.status == NodeStatus.DONE:
            return "done"
        now = now or datetime.now(timezone.utc)
        if is_routine_due(node.next_due_at, now):
            return "overdue"
        if parse_iso_datetime(node.next_due_at) is not None:
            return "due"
        return "scheduled"

    def due_routines(self, graph: GraphModel, now: datetime | None = None) -> list[Node]:
        return [
            node
            for node in graph.nodes.values()
            if node.type == NodeType.ROUTINE and self.routine_state(node, now) == "overdue"
        ]

    def upcoming_routines(
        self, graph: GraphModel, now: datetime | None = None
    ) -> list[Node]:
        return [
            node
            for node in graph.nodes.values()
            if node.type == NodeType.ROUTINE and self.routine_state(node, now) == "due"
        ]
