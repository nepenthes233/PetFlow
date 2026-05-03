from __future__ import annotations

import unittest

from petflow.domain import DependencyCycleError, Edge, EdgeType, GraphModel, Node, NodeType


class GraphModelTest(unittest.TestCase):
    def test_dependency_cycle_is_rejected(self) -> None:
        graph = GraphModel()
        graph.add_node(Node(id="a", type=NodeType.TASK, title="A"))
        graph.add_node(Node(id="b", type=NodeType.TASK, title="B"))

        graph.add_edge(Edge(id="ab", source="a", target="b", type=EdgeType.DEPENDENCY))

        with self.assertRaises(DependencyCycleError):
            graph.add_edge(
                Edge(id="ba", source="b", target="a", type=EdgeType.DEPENDENCY)
            )

    def test_routine_cycle_is_allowed(self) -> None:
        graph = GraphModel()
        graph.add_node(Node(id="a", type=NodeType.TASK, title="A"))
        graph.add_node(Node(id="b", type=NodeType.TASK, title="B"))

        graph.add_edge(Edge(id="ab", source="a", target="b", type=EdgeType.ROUTINE))
        graph.add_edge(Edge(id="ba", source="b", target="a", type=EdgeType.ROUTINE))

        self.assertEqual(len(graph.edges), 2)


if __name__ == "__main__":
    unittest.main()
