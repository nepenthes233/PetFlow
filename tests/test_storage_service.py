from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from petflow.app import AppContext
from petflow.domain import EdgeType, NodeStatus, NodeType
from petflow.domain.enums import PetStateType
from petflow.services import StorageService


class StorageServiceTest(unittest.TestCase):
    def test_save_and_load_graph_round_trip(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(
            title="Design model",
            node_type=NodeType.TASK,
            status=NodeStatus.DONE,
            priority=4,
            estimated_minutes=60,
            x=120,
            y=160,
        )
        second = context.graph_service.create_node(
            title="Build UI",
            node_type=NodeType.TASK,
            priority=5,
            estimated_minutes=120,
            x=320,
            y=160,
        )
        context.graph_service.create_edge(
            first.id,
            second.id,
            EdgeType.DEPENDENCY,
            label="blocks",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "graph.json"
            storage = StorageService()
            storage.save_graph(context.graph, path)

            loaded = storage.load_graph(path)

        self.assertEqual(len(loaded.nodes), 2)
        self.assertEqual(len(loaded.edges), 1)
        loaded_first = loaded.get_node(first.id)
        self.assertIsNotNone(loaded_first)
        assert loaded_first is not None
        self.assertEqual(loaded_first.title, "Design model")
        self.assertEqual(loaded_first.status, NodeStatus.DONE)
        self.assertEqual(loaded_first.x, 120)
        self.assertEqual(len(loaded.edges), 1)
        edge = next(iter(loaded.edges.values()))
        self.assertEqual(edge.type, EdgeType.DEPENDENCY)
        self.assertEqual(edge.label, "blocks")

    def test_save_and_load_pet_state(self) -> None:
        context = AppContext.create()
        node = context.graph_service.create_node(title="Current task", x=200, y=220)
        context.pet_service.move_to_node(
            node.id,
            state=PetStateType.THINK,
            speech="Try this next",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "graph.json"
            storage = StorageService()
            storage.save_graph(context.graph, path)

            loaded = storage.load_graph(path)

        self.assertEqual(loaded.pet.current_node_id, node.id)
        self.assertEqual(loaded.pet.state, PetStateType.THINK)
        self.assertEqual(loaded.pet.speech, "Try this next")
        self.assertGreater(loaded.pet.x, node.x)


if __name__ == "__main__":
    unittest.main()
