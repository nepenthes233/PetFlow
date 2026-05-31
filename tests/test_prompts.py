from __future__ import annotations

import unittest

from petflow.agent.prompts import PromptBuilder
from petflow.app import AppContext


class PromptBuilderTest(unittest.TestCase):
    def test_companion_prompt_preserves_proposal_contract_and_context(self) -> None:
        context = AppContext.create()
        context.graph_service.create_node(title="Existing task")

        prompt = PromptBuilder().build_companion_planning_prompt(
            "Plan my project demo", context.graph
        )

        self.assertIn("nodes", prompt)
        self.assertIn("edges", prompt)
        self.assertIn("Existing task", prompt)
        self.assertIn("node_", prompt)
        self.assertIn("delete_node_ids", prompt)
        self.assertIn("delete_all_nodes", prompt)
        self.assertIn("delete_query", prompt)
        self.assertIn("update_nodes", prompt)
        self.assertIn("add_edges", prompt)
        self.assertIn("layout", prompt)
        self.assertIn("deadline", prompt)
        self.assertIn("repeat_type", prompt)
        self.assertIn("routine", prompt)
        self.assertIn("Plan my project demo", prompt)
        self.assertIn("Every edge source and target", prompt)

    def test_generation_prompt_requests_only_structured_json(self) -> None:
        prompt = PromptBuilder().build_graph_generation_prompt("Build a demo")

        self.assertIn("Return only a JSON object", prompt)
        self.assertIn("Build a demo", prompt)

    def test_companion_chat_prompt_requests_reply_without_graph_changes(self) -> None:
        context = AppContext.create()

        prompt = PromptBuilder().build_companion_chat_prompt(
            "How should I prioritize today?", context.graph
        )

        self.assertIn("`reply` string field", prompt)
        self.assertIn("Do not generate or modify task nodes", prompt)
        self.assertIn("How should I prioritize today?", prompt)


if __name__ == "__main__":
    unittest.main()
