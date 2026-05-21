from __future__ import annotations

import unittest

from petflow.domain import (
    DependencyCycleError,
    Edge,
    EdgeType,
    GraphModel,
    Node,
    NodeType,
)


class GraphModelTest(unittest.TestCase):
    def _graph_with_two_nodes(self) -> GraphModel:
        graph = GraphModel()
        graph.add_node(Node(id="a", type=NodeType.TASK, title="A"))
        graph.add_node(Node(id="b", type=NodeType.TASK, title="B"))
        return graph

    def test_dependency_cycle_is_rejected(self) -> None:
        graph = self._graph_with_two_nodes()

        graph.add_edge(Edge(id="ab", source="a", target="b", type=EdgeType.DEPENDENCY))

        with self.assertRaises(DependencyCycleError):
            graph.add_edge(
                Edge(id="ba", source="b", target="a", type=EdgeType.DEPENDENCY)
            )

    def test_routine_cycle_is_allowed(self) -> None:
        graph = self._graph_with_two_nodes()

        graph.add_edge(Edge(id="ab", source="a", target="b", type=EdgeType.ROUTINE))
        graph.add_edge(Edge(id="ba", source="b", target="a", type=EdgeType.ROUTINE))

        self.assertEqual(len(graph.edges), 2)

    def test_update_edge_rejects_dependency_cycle(self) -> None:
        graph = self._graph_with_two_nodes()
        graph.add_edge(Edge(id="ab", source="a", target="b", type=EdgeType.DEPENDENCY))
        graph.add_edge(Edge(id="ba", source="b", target="a", type=EdgeType.ROUTINE))

        with self.assertRaises(DependencyCycleError):
            graph.update_edge("ba", type=EdgeType.DEPENDENCY)

    def test_update_edge_allows_routine_cycle(self) -> None:
        graph = self._graph_with_two_nodes()
        graph.add_edge(Edge(id="ab", source="a", target="b", type=EdgeType.DEPENDENCY))
        graph.add_edge(Edge(id="ba", source="b", target="a", type=EdgeType.TRIGGER))

        edge = graph.update_edge("ba", type=EdgeType.ROUTINE, label="repeat")

        self.assertEqual(edge.type, EdgeType.ROUTINE)
        self.assertEqual(edge.label, "repeat")


if __name__ == "__main__":
    unittest.main()
