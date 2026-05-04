from __future__ import annotations

import unittest

from petflow.domain import GraphValidationError, Node, NodeType
from petflow.services import ResourceService


class ResourceServiceTest(unittest.TestCase):
    def test_resource_text_prefers_resource_path(self) -> None:
        service = ResourceService()
        node = Node(
            id="resource",
            type=NodeType.RESOURCE,
            title="Docs",
            description="fallback",
            resource_path="https://example.com",
        )

        self.assertEqual(service.resource_text(node), "https://example.com")

    def test_resource_text_uses_description_fallback(self) -> None:
        service = ResourceService()
        node = Node(
            id="resource",
            type=NodeType.RESOURCE,
            title="Notes",
            description="Remember this",
        )

        self.assertEqual(service.resource_text(node), "Remember this")

    def test_resource_text_rejects_empty_non_resource(self) -> None:
        service = ResourceService()
        node = Node(id="task", type=NodeType.TASK, title="Task")

        with self.assertRaises(GraphValidationError):
            service.resource_text(node)


if __name__ == "__main__":
    unittest.main()
