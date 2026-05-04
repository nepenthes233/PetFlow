from __future__ import annotations

import unittest

from petflow.app import AppContext
from petflow.domain import EdgeType, GraphValidationError, NodeStatus, NodeType


class GraphServiceTest(unittest.TestCase):
    def test_create_node_trims_title_and_sets_fields(self) -> None:
        context = AppContext.create()

        node = context.graph_service.create_node(
            title="  Write report  ",
            node_type=NodeType.TASK,
            description="  Draft final report  ",
            status=NodeStatus.DOING,
            priority=5,
            estimated_minutes=90,
        )

        self.assertEqual(node.title, "Write report")
        self.assertEqual(node.description, "Draft final report")
        self.assertEqual(node.status, NodeStatus.DOING)
        self.assertEqual(node.priority, 5)
        self.assertEqual(node.estimated_minutes, 90)

    def test_create_node_rejects_invalid_values(self) -> None:
        context = AppContext.create()

        with self.assertRaises(GraphValidationError):
            context.graph_service.create_node(title="")

        with self.assertRaises(GraphValidationError):
            context.graph_service.create_node(title="Task", priority=0)

        with self.assertRaises(GraphValidationError):
            context.graph_service.create_node(title="Task", estimated_minutes=-1)

    def test_update_node_detail_validates_values(self) -> None:
        context = AppContext.create()
        node = context.graph_service.create_node(title="Task")

        updated = context.graph_service.update_node_detail(
            node.id,
            title="Updated",
            description="More detail",
            node_type=NodeType.ROUTINE,
            status=NodeStatus.PAUSED,
            priority=2,
            estimated_minutes=45,
        )

        self.assertEqual(updated.title, "Updated")
        self.assertEqual(updated.type, NodeType.ROUTINE)
        self.assertEqual(updated.status, NodeStatus.PAUSED)

    def test_create_edge_stores_type_and_trimmed_label(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(title="First")
        second = context.graph_service.create_node(title="Second")

        edge = context.graph_service.create_edge(
            first.id,
            second.id,
            EdgeType.TRIGGER,
            label="  unlocks next task  ",
        )

        self.assertEqual(edge.source, first.id)
        self.assertEqual(edge.target, second.id)
        self.assertEqual(edge.type, EdgeType.TRIGGER)
        self.assertEqual(edge.label, "unlocks next task")

    def test_update_edge_stores_type_and_trimmed_label(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(title="First")
        second = context.graph_service.create_node(title="Second")
        edge = context.graph_service.create_edge(first.id, second.id)

        updated = context.graph_service.update_edge(
            edge.id,
            type=EdgeType.RECOMMENDATION.value,
            label="  read before starting  ",
        )

        self.assertEqual(updated.type, EdgeType.RECOMMENDATION)
        self.assertEqual(updated.label, "read before starting")

    def test_edge_label_length_is_limited(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(title="First")
        second = context.graph_service.create_node(title="Second")

        with self.assertRaises(GraphValidationError):
            context.graph_service.create_edge(first.id, second.id, label="x" * 81)


if __name__ == "__main__":
    unittest.main()
