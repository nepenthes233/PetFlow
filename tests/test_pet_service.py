from __future__ import annotations

import unittest

from petflow.app import AppContext
from petflow.domain import EdgeType, NodeStatus
from petflow.domain.enums import PetStateType


class PetServiceTest(unittest.TestCase):
    def test_done_node_moves_pet_to_next_recommended_node(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(
            title="First",
            priority=1,
            x=100,
            y=120,
        )
        second = context.graph_service.create_node(
            title="Second",
            priority=5,
            x=360,
            y=180,
        )
        context.graph_service.create_edge(first.id, second.id, EdgeType.DEPENDENCY)

        context.graph_service.update_node_status(first.id, NodeStatus.DONE)

        self.assertEqual(context.graph.pet.current_node_id, second.id)
        self.assertEqual(context.graph.pet.state, PetStateType.HAPPY)
        self.assertIn("Second", context.graph.pet.speech)
        self.assertGreater(context.graph.pet.x, second.x)

    def test_react_to_recommendation_handles_empty_graph(self) -> None:
        context = AppContext.create()

        context.pet_service.react_to_recommendation(None)

        self.assertEqual(context.graph.pet.state, PetStateType.IDLE)
        self.assertEqual(context.graph.pet.speech, "No available next step.")


if __name__ == "__main__":
    unittest.main()
