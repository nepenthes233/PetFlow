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

    def test_format_agent_review_uses_summary_and_highlights(self) -> None:
        review = ReviewService().format_agent_review(
            {
                "summary": "Good progress today.",
                "highlights": ["Finished setup", "Next: polish Agent"],
            },
            fallback="fallback",
        )

        self.assertIn("Good progress today.", review)
        self.assertIn("- Finished setup", review)

    def test_format_agent_review_falls_back_without_summary(self) -> None:
        review = ReviewService().format_agent_review({}, fallback="fallback")

        self.assertEqual(review, "fallback")


if __name__ == "__main__":
    unittest.main()
