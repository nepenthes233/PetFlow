from __future__ import annotations

import unittest
from datetime import datetime

from petflow.app import AppContext
from petflow.domain import EdgeType, GraphValidationError, NodeStatus, NodeType
from petflow.domain.enums import RepeatType, ResourceType


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

        with self.assertRaises(GraphValidationError):
            context.graph_service.create_node(title="Task", actual_minutes=-1)

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

    def test_update_node_detail_routes_status_change_through_history(self) -> None:
        context = AppContext.create()
        node = context.graph_service.create_node(title="Task")

        updated = context.graph_service.update_node_detail(
            node.id,
            title="Task",
            description="",
            node_type=NodeType.TASK,
            status=NodeStatus.DONE,
            priority=3,
            estimated_minutes=30,
        )

        self.assertEqual(updated.status, NodeStatus.DONE)
        self.assertIsNotNone(updated.completed_at)
        self.assertEqual(context.graph.history[-2]["action"], "node.status_changed")

    def test_update_node_detail_updates_resource_and_checklist_fields(self) -> None:
        context = AppContext.create()
        node = context.graph_service.create_node(title="Task")

        updated = context.graph_service.update_node_detail(
            node.id,
            title="Resource task",
            description="",
            node_type=NodeType.RESOURCE,
            status=NodeStatus.TODO,
            priority=2,
            estimated_minutes=0,
            actual_minutes=5,
            tags=["reference", " reference ", "course"],
            resource_type=ResourceType.TEXT,
            resource_path="notes.txt",
            checklist=["collect links", "summarize"],
        )

        self.assertEqual(updated.actual_minutes, 5)
        self.assertEqual(updated.tags, ["reference", "course"])
        self.assertEqual(updated.resource_type, ResourceType.TEXT)
        self.assertEqual(updated.resource_path, "notes.txt")
        self.assertEqual(
            [item.text for item in updated.checklist],
            ["collect links", "summarize"],
        )

    def test_create_node_accepts_routine_fields(self) -> None:
        context = AppContext.create()

        node = context.graph_service.create_node(
            title="Weekly review",
            node_type=NodeType.ROUTINE,
            repeat_type=RepeatType.WEEKLY,
            next_due_at="2026-05-05T00:00:00+00:00",
            streak=2,
        )

        self.assertEqual(node.repeat_type, RepeatType.WEEKLY)
        self.assertEqual(node.next_due_at, "2026-05-05T00:00:00+00:00")
        self.assertEqual(node.streak, 2)

    def test_create_node_accepts_detail_fields(self) -> None:
        context = AppContext.create()

        node = context.graph_service.create_node(
            title="Read docs",
            actual_minutes=12,
            tags=[" docs ", "docs", "python"],
            resource_type=ResourceType.URL,
            resource_path=" https://example.com ",
            checklist=[" skim ", "", "take notes"],
        )

        self.assertEqual(node.actual_minutes, 12)
        self.assertEqual(node.tags, ["docs", "python"])
        self.assertEqual(node.resource_type, ResourceType.URL)
        self.assertEqual(node.resource_path, "https://example.com")
        self.assertEqual([item.text for item in node.checklist], ["skim", "take notes"])

    def test_create_resource_node_sets_resource_fields(self) -> None:
        context = AppContext.create()

        node = context.graph_service.create_resource_node(
            title="example.com",
            resource_type=ResourceType.URL,
            resource_path="https://example.com",
            description="https://example.com",
        )

        self.assertEqual(node.type, NodeType.RESOURCE)
        self.assertEqual(node.resource_type, ResourceType.URL)
        self.assertEqual(node.resource_path, "https://example.com")

    def test_add_node_attachment_stores_unique_paths(self) -> None:
        context = AppContext.create()
        node = context.graph_service.create_node(title="Task")

        context.graph_service.add_node_attachment(node.id, "/tmp/report.pdf")
        updated = context.graph_service.add_node_attachment(node.id, "/tmp/report.pdf")

        self.assertEqual(updated.attachments, ["/tmp/report.pdf"])

    def test_update_node_rejects_direct_status_change(self) -> None:
        context = AppContext.create()
        node = context.graph_service.create_node(title="Task")

        with self.assertRaises(GraphValidationError):
            context.graph_service.update_node(node.id, status=NodeStatus.DONE)

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

    def test_update_node_status_records_history_and_completion_time(self) -> None:
        context = AppContext.create()
        node = context.graph_service.create_node(title="Task")

        updated = context.graph_service.update_node_status(node.id, NodeStatus.DONE)

        self.assertEqual(updated.status, NodeStatus.DONE)
        self.assertIsNotNone(updated.completed_at)
        self.assertEqual(context.graph.history[-2]["action"], "node.status_changed")
        self.assertEqual(context.graph.history[-1]["action"], "node.completed")

    def test_routine_done_updates_streak_and_next_due_at(self) -> None:
        context = AppContext.create()
        node = context.graph_service.create_node(
            title="Daily review",
            node_type=NodeType.ROUTINE,
        )
        context.graph_service.update_node(
            node.id,
            repeat_type=RepeatType.DAILY,
            repeat_interval=2,
            streak=3,
        )

        updated = context.graph_service.update_node_status(node.id, NodeStatus.DONE)

        self.assertEqual(updated.streak, 4)
        self.assertIsNotNone(updated.last_completed_at)
        self.assertIsNotNone(updated.next_due_at)
        assert updated.last_completed_at is not None
        assert updated.next_due_at is not None
        completed_at = datetime.fromisoformat(updated.last_completed_at)
        next_due_at = datetime.fromisoformat(updated.next_due_at)
        self.assertEqual((next_due_at - completed_at).days, 2)


if __name__ == "__main__":
    unittest.main()
