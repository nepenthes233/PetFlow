from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from petflow.app import AppContext
from petflow.domain.enums import NodeStatus, NodeType, RepeatType


class AgendaServiceTest(unittest.TestCase):
    def test_groups_pending_scheduled_nodes_for_next_seven_days(self) -> None:
        context = AppContext.create()
        now = datetime(2026, 5, 25, 10, tzinfo=timezone.utc)
        tomorrow = (now + timedelta(days=1)).isoformat()
        important = context.graph_service.create_node(
            title="Important",
            priority=5,
            next_due_at=tomorrow,
        )
        routine = context.graph_service.create_node(
            title="Routine",
            node_type=NodeType.ROUTINE,
            priority=2,
            next_due_at=tomorrow,
        )
        done = context.graph_service.create_node(
            title="Completed",
            status=NodeStatus.DONE,
            next_due_at=tomorrow,
        )
        context.graph_service.create_node(
            title="Outside window",
            next_due_at=(now + timedelta(days=7)).isoformat(),
        )

        days = context.agenda_service.upcoming_days(context.graph, now=now)

        self.assertEqual(len(days), 7)
        self.assertEqual(
            [node.id for node in days[1].nodes],
            [important.id, routine.id],
        )
        self.assertNotIn(done.id, [node.id for day in days for node in day.nodes])

    def test_resources_and_unscheduled_nodes_are_not_daily_todos(self) -> None:
        context = AppContext.create()
        now = datetime(2026, 5, 25, 10, tzinfo=timezone.utc)
        context.graph_service.create_node(title="No due date")
        context.graph_service.create_node(
            title="Resource",
            node_type=NodeType.RESOURCE,
            next_due_at=now.isoformat(),
        )

        days = context.agenda_service.upcoming_days(context.graph, now=now)

        self.assertFalse(any(day.nodes for day in days))

    def test_repeating_task_is_expanded_across_visible_days(self) -> None:
        context = AppContext.create()
        now = datetime(2026, 5, 25, 10, tzinfo=timezone.utc)
        routine = context.graph_service.create_node(
            title="Stretch",
            node_type=NodeType.ROUTINE,
            next_due_at="2026-05-26",
            repeat_type=RepeatType.DAILY,
            repeat_interval=2,
        )

        days = context.agenda_service.upcoming_days(context.graph, now=now)

        visible_dates = [
            day.date.isoformat() for day in days if routine in day.nodes
        ]
        self.assertEqual(visible_dates, ["2026-05-26", "2026-05-28", "2026-05-30"])


if __name__ == "__main__":
    unittest.main()
