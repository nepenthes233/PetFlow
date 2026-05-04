from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from petflow.app import AppContext
from petflow.domain import EdgeType, NodeStatus, NodeType
from petflow.domain.enums import RepeatType


class RecommendationEngineTest(unittest.TestCase):
    def test_dependency_must_be_done_before_target_is_recommended(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(title="First", priority=1)
        second = context.graph_service.create_node(title="Second", priority=5)
        context.graph_service.create_edge(first.id, second.id, EdgeType.DEPENDENCY)

        recommended = context.recommendation_engine.recommend_next(context.graph)

        self.assertEqual(recommended, first)

        context.graph_service.update_node_status(first.id, NodeStatus.DONE)
        recommended = context.recommendation_engine.recommend_next(context.graph)

        self.assertEqual(recommended, second)

    def test_done_and_blocked_nodes_are_not_recommended(self) -> None:
        context = AppContext.create()
        context.graph_service.create_node(
            title="Done",
            status=NodeStatus.DONE,
            priority=5,
        )
        context.graph_service.create_node(
            title="Blocked",
            status=NodeStatus.BLOCKED,
            priority=5,
        )
        available = context.graph_service.create_node(title="Available", priority=1)

        recommended = context.recommendation_engine.recommend_next(context.graph)

        self.assertEqual(recommended, available)

    def test_doing_status_beats_higher_todo_priority(self) -> None:
        context = AppContext.create()
        doing = context.graph_service.create_node(
            title="In progress",
            status=NodeStatus.DOING,
            priority=2,
        )
        context.graph_service.create_node(title="Important todo", priority=4)

        recommended = context.recommendation_engine.recommend_next(context.graph)

        self.assertEqual(recommended, doing)

    def test_due_routine_is_weighted_above_regular_task(self) -> None:
        context = AppContext.create()
        routine = context.graph_service.create_node(
            title="Daily review",
            node_type=NodeType.ROUTINE,
            priority=2,
        )
        context.graph_service.update_node(
            routine.id,
            repeat_type=RepeatType.DAILY,
            next_due_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        )
        context.graph_service.create_node(title="Regular task", priority=4)

        recommended = context.recommendation_engine.recommend_next(context.graph)

        self.assertEqual(recommended, routine)


if __name__ == "__main__":
    unittest.main()
