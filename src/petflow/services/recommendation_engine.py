from __future__ import annotations

from petflow.domain.entities import Node
from petflow.domain.enums import EdgeType, NodeStatus, NodeType
from petflow.domain.graph import GraphModel
from petflow.domain.routine import is_routine_due


class RecommendationEngine:
    def recommend_next(self, graph: GraphModel) -> Node | None:
        candidates = [
            node
            for node in graph.nodes.values()
            if self._is_candidate(graph, node)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda node: self._score(graph, node), reverse=True)
        return candidates[0]

    def _score(self, graph: GraphModel, node: Node) -> int:
        score = node.priority * 10
        if node.status == NodeStatus.DOING:
            score += 35
        if node.status == NodeStatus.PAUSED:
            score -= 10
        if node.type == NodeType.ROUTINE:
            score += 10
            if is_routine_due(node.next_due_at):
                score += 40
        if node.type == NodeType.REWARD:
            score += 5
        if graph.workspace.current_node_id == node.id:
            score += 10
        return score

    def recommend_reason(self, graph: GraphModel, node: Node) -> str:
        reasons: list[str] = []
        if self._dependencies_done(graph, node):
            reasons.append("dependencies ready")
        if node.status == NodeStatus.DOING:
            reasons.append("already in progress")
        if node.status == NodeStatus.PAUSED:
            reasons.append("paused but still relevant")
        if node.type == NodeType.ROUTINE:
            if is_routine_due(node.next_due_at):
                reasons.append("routine is due")
            else:
                reasons.append("routine scheduled")
        if node.priority >= 4:
            reasons.append("high priority")
        if graph.workspace.current_node_id == node.id:
            reasons.append("current focus")
        if not reasons:
            reasons.append("best available next step")
        return ", ".join(reasons)

    def _is_candidate(self, graph: GraphModel, node: Node) -> bool:
        if node.status in {NodeStatus.DONE, NodeStatus.BLOCKED}:
            return False
        return self._dependencies_done(graph, node)

    def _dependencies_done(self, graph: GraphModel, node: Node) -> bool:
        for predecessor in graph.predecessors(node.id, [EdgeType.DEPENDENCY]):
            if predecessor.status != NodeStatus.DONE:
                return False
        return True
