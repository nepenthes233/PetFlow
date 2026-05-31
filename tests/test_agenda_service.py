from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from petflow.app import AppContext
from petflow.domain.graph import GraphModel
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

    def test_repeating_node_without_due_date_starts_today(self) -> None:
        context = AppContext.create()
        now = datetime(2026, 5, 25, 10, tzinfo=timezone.utc)
        routine = context.graph_service.create_node(
            title="Weekly cleanup",
            node_type=NodeType.ROUTINE,
            repeat_type=RepeatType.WEEKLY,
        )

        days = context.agenda_service.upcoming_days(context.graph, now=now)

        self.assertIn(routine, days[0].nodes)

    def test_legacy_nested_routine_fields_are_scheduled(self) -> None:
        now = datetime(2026, 5, 25, 10, tzinfo=timezone.utc)
        graph = GraphModel.from_dict(
            {
                "nodes": [
                    {
                        "id": "routine_1",
                        "type": "routine",
                        "title": "Legacy routine",
                        "routine": {
                            "recurrence": "daily",
                            "interval_days": 2,
                            "next_due_at": "2026-05-23",
                            "streak": 3,
                        },
                    }
                ],
                "edges": [],
            }
        )
        routine = graph.get_node("routine_1")
        assert routine is not None

        days = AppContext.create().agenda_service.upcoming_days(graph, now=now)

        self.assertEqual(routine.repeat_type, RepeatType.DAILY)
        self.assertEqual(routine.repeat_interval, 2)
        self.assertEqual(routine.next_due_at, "2026-05-23")
        self.assertEqual(routine.streak, 3)
        visible_dates = [
            day.date.isoformat() for day in days if routine in day.nodes
        ]
        self.assertEqual(
            visible_dates,
            ["2026-05-25", "2026-05-27", "2026-05-29", "2026-05-31"],
        )


if __name__ == "__main__":
    unittest.main()
