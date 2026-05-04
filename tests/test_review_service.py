from __future__ import annotations

import unittest

from petflow.app import AppContext
from petflow.domain import NodeStatus, NodeType
from petflow.services import ReviewService


class ReviewServiceTest(unittest.TestCase):
    def test_summary_text_counts_graph_state(self) -> None:
        context = AppContext.create()
        completed = context.graph_service.create_node(
            title="Done task",
            status=NodeStatus.DONE,
        )
        context.graph_service.create_node(title="Active task")
        context.graph_service.create_node(
            title="Blocked task",
            status=NodeStatus.BLOCKED,
        )
        context.graph_service.create_node(
            title="Daily routine",
            node_type=NodeType.ROUTINE,
        )
        context.graph.record_history("node.completed", {"node_id": completed.id})

        summary = ReviewService().summary_text(context.graph)

        self.assertIn("Completed: 1", summary)
        self.assertIn("Active: 2", summary)
        self.assertIn("Blocked: 1", summary)
        self.assertIn("Routines: 1", summary)
        self.assertIn("History entries: 1", summary)


if __name__ == "__main__":
    unittest.main()
