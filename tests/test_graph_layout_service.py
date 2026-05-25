from __future__ import annotations

import unittest

from petflow.app import AppContext
from petflow.domain.enums import EdgeType, NodeType
from petflow.services import GraphLayoutService


class GraphLayoutServiceTest(unittest.TestCase):
    def test_grid_positions_are_stable_and_non_overlapping(self) -> None:
        context = AppContext.create()
        nodes = [
            context.graph_service.create_node(title=f"Task {index}", x=0, y=0)
            for index in range(5)
        ]
        service = GraphLayoutService(
            start_x=10,
            start_y=20,
            column_gap=100,
            row_gap=80,
        )

        positions = service.grid_positions(context.graph)

        self.assertEqual(set(positions), {node.id for node in nodes})
        self.assertEqual(positions[nodes[0].id], (10, 20))
        self.assertEqual(positions[nodes[1].id], (110, 20))
        self.assertEqual(positions[nodes[3].id], (10, 100))

    def test_apply_grid_layout_moves_nodes_through_graph_service(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(title="First", x=500, y=500)
        second = context.graph_service.create_node(title="Second", x=500, y=500)
        service = GraphLayoutService(start_x=30, start_y=40)

        service.apply_grid_layout(context.graph_service)

        self.assertEqual((first.x, first.y), (30, 40))
        self.assertGreater(second.x, first.x)

    def test_apply_subset_grid_layout_places_new_nodes_below_existing_graph(self) -> None:
        context = AppContext.create()
        context.graph_service.create_node(title="Existing", x=30, y=300)
        first = context.graph_service.create_node(title="New 1", x=0, y=0)
        second = context.graph_service.create_node(title="New 2", x=0, y=0)
        service = GraphLayoutService(start_x=30, start_y=40, row_gap=80)

        service.apply_subset_grid_layout(context.graph_service, [first.id, second.id])

        self.assertEqual(first.y, 380)
        self.assertEqual(second.y, 380)
        self.assertGreater(second.x, first.x)

    def test_flow_positions_put_resources_below_and_rewards_after_main_path(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(title="First")
        second = context.graph_service.create_node(title="Second")
        resource = context.graph_service.create_node(
            title="Docs", node_type=NodeType.RESOURCE
        )
        reward = context.graph_service.create_node(
            title="Celebrate", node_type=NodeType.REWARD
        )
        context.graph_service.create_edge(first.id, second.id, EdgeType.DEPENDENCY)
        context.graph.workspace.current_node_id = second.id
        service = GraphLayoutService(start_x=20, start_y=30, column_gap=240, row_gap=130)

        positions = service.flow_positions(context.graph)

        self.assertGreater(positions[second.id][0], positions[first.id][0])
        self.assertGreater(positions[resource.id][1], positions[first.id][1])
        self.assertEqual(positions[resource.id][0], positions[second.id][0])
        self.assertGreater(positions[reward.id][0], positions[second.id][0])


if __name__ == "__main__":
    unittest.main()
