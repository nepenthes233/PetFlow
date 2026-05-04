from __future__ import annotations

import unittest

from petflow.agent.agent_client import AgentClient
from petflow.agent.agent_executor import AgentExecutor
from petflow.agent.proposal import AgentProposalValidator
from petflow.app import AppContext
from petflow.domain import EdgeType, GraphValidationError, NodeType


class AgentWorkflowTest(unittest.TestCase):
    def test_validator_accepts_valid_proposal(self) -> None:
        validator = AgentProposalValidator()
        proposal = validator.validate(
            {
                "nodes": [
                    {"id": "n1", "title": "Task 1", "type": "task"},
                    {"id": "n2", "title": "Task 2", "type": "task"},
                ],
                "edges": [{"source": "n1", "target": "n2", "type": "dependency"}],
            }
        )

        self.assertEqual(len(proposal["nodes"]), 2)
        self.assertEqual(len(proposal["edges"]), 1)

    def test_validator_rejects_missing_title(self) -> None:
        validator = AgentProposalValidator()

        with self.assertRaises(GraphValidationError):
            validator.validate({"nodes": [{"id": "n1"}], "edges": []})

    def test_mock_client_returns_graph_proposal(self) -> None:
        client = AgentClient(mock_mode=True)

        proposal = client.complete_json("generate a graph")

        self.assertIn("nodes", proposal)
        self.assertIn("edges", proposal)

    def test_executor_applies_proposal(self) -> None:
        context = AppContext.create()
        executor = AgentExecutor(context.graph_service)

        executor.apply_graph_proposal(
            {
                "nodes": [
                    {"id": "n1", "title": "Plan", "type": "task"},
                    {"id": "n2", "title": "Build", "type": "task"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2", "type": "dependency"},
                ],
            }
        )

        self.assertEqual(len(context.graph.nodes), 2)
        self.assertEqual(len(context.graph.edges), 1)
        self.assertEqual(next(iter(context.graph.edges.values())).type, EdgeType.DEPENDENCY)
        self.assertEqual(next(iter(context.graph.nodes.values())).type, NodeType.TASK)

    def test_executor_links_split_nodes_to_parent(self) -> None:
        context = AppContext.create()
        parent = context.graph_service.create_node(title="Complex task")
        executor = AgentExecutor(context.graph_service)

        created = executor.apply_graph_proposal(
            {
                "nodes": [{"id": "n1", "title": "Subtask", "type": "task"}],
                "edges": [],
            },
            parent_node_id=parent.id,
        )

        self.assertEqual(len(created), 1)
        recommendation_edges = [
            edge
            for edge in context.graph.edges.values()
            if edge.source == parent.id and edge.target == created[0].id
        ]
        self.assertEqual(len(recommendation_edges), 1)
        self.assertEqual(recommendation_edges[0].type, EdgeType.RECOMMENDATION)


if __name__ == "__main__":
    unittest.main()
