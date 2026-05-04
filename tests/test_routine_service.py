from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from petflow.app import AppContext
from petflow.domain.enums import NodeType, RepeatType


class RoutineServiceTest(unittest.TestCase):
    def test_due_and_upcoming_routines_are_classified(self) -> None:
        context = AppContext.create()
        overdue = context.graph_service.create_node(
            title="Overdue",
            node_type=NodeType.ROUTINE,
        )
        due = context.graph_service.create_node(
            title="Due",
            node_type=NodeType.ROUTINE,
        )
        scheduled = context.graph_service.create_node(
            title="Scheduled",
            node_type=NodeType.ROUTINE,
        )
        context.graph_service.update_node(
            overdue.id,
            repeat_type=RepeatType.DAILY,
            next_due_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        )
        context.graph_service.update_node(
            due.id,
            repeat_type=RepeatType.DAILY,
            next_due_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        )

        self.assertEqual(
            [node.id for node in context.routine_service.due_routines(context.graph)],
            [overdue.id],
        )
        self.assertEqual(
            [node.id for node in context.routine_service.upcoming_routines(context.graph)],
            [due.id],
        )
        self.assertEqual(context.routine_service.routine_state(scheduled), "scheduled")


if __name__ == "__main__":
    unittest.main()
