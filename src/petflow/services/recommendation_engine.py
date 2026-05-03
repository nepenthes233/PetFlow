from __future__ import annotations

from petflow.domain.entities import Node
from petflow.domain.enums import EdgeType, NodeStatus, NodeType
from petflow.domain.graph import GraphModel


class RecommendationEngine:
    def recommend_next(self, graph: GraphModel) -> Node | None:
        candidates = [
            node
            for node in graph.nodes.values()
            if node.status != NodeStatus.DONE and self._dependencies_done(graph, node)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda node: self._score(graph, node), reverse=True)
        return candidates[0]

    def _score(self, graph: GraphModel, node: Node) -> int:
        score = node.priority * 10
        if node.status == NodeStatus.DOING:
            score += 20
        if node.type == NodeType.ROUTINE:
            score += 15
        if node.type == NodeType.REWARD:
            score += 5
        if graph.workspace.current_node_id == node.id:
            score += 10
        return score

    def _dependencies_done(self, graph: GraphModel, node: Node) -> bool:
        for predecessor in graph.predecessors(node.id, [EdgeType.DEPENDENCY]):
            if predecessor.status != NodeStatus.DONE:
                return False
        return True
