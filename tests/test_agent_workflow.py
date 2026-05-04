from __future__ import annotations

import os
import unittest
from unittest.mock import patch

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

    def test_validator_rejects_duplicate_node_ids(self) -> None:
        validator = AgentProposalValidator()

        with self.assertRaises(GraphValidationError):
            validator.validate(
                {
                    "nodes": [
                        {"id": "n1", "title": "Task 1"},
                        {"id": "n1", "title": "Task 2"},
                    ],
                    "edges": [],
                }
            )

    def test_validator_rejects_too_many_nodes(self) -> None:
        validator = AgentProposalValidator(max_nodes=2)

        with self.assertRaises(GraphValidationError):
            validator.validate(
                {
                    "nodes": [
                        {"id": "n1", "title": "Task 1"},
                        {"id": "n2", "title": "Task 2"},
                        {"id": "n3", "title": "Task 3"},
                    ],
                    "edges": [],
                }
            )

    def test_mock_client_returns_graph_proposal(self) -> None:
        client = AgentClient(mock_mode=True)

        proposal = client.complete_json("generate a graph")

        self.assertIn("nodes", proposal)
        self.assertIn("edges", proposal)

    def test_mock_client_connection_test_succeeds(self) -> None:
        client = AgentClient(mock_mode=True)

        self.assertEqual(client.test_connection(), "Mock mode is available.")

    def test_client_connection_test_uses_api(self) -> None:
        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"choices": [{"message": {"content": '{"ok": true}'}}]}

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

        client = AgentClient(
            api_key="test-key",
            mock_mode=False,
            http_post=fake_post,
        )

        self.assertEqual(client.test_connection(), "Agent API is reachable.")

    def test_client_connection_test_uses_responses_api(self) -> None:
        captured: dict[str, object] = {}

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"output_text": '{"ok": true}'}

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            captured["args"] = args
            captured["kwargs"] = kwargs
            return FakeResponse()

        client = AgentClient(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            wire_api="responses",
            mock_mode=False,
            http_post=fake_post,
        )

        self.assertEqual(client.test_connection(), "Agent API is reachable.")
        self.assertEqual(captured["args"][0], "https://api.example.com/v1/responses")

    def test_client_reads_image_api_key_fallback(self) -> None:
        with patch.dict(
            os.environ,
            {
                "IMAGE_API_KEY": "test-key",
                "PETFLOW_AGENT_API_KEY": "",
                "PETFLOW_AGENT_MOCK": "",
            },
            clear=False,
        ):
            client = AgentClient.from_environment()

        self.assertEqual(client.api_key, "test-key")

    def test_client_parses_chat_completion_json_response(self) -> None:
        captured: dict[str, object] = {}

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"nodes":[{"id":"n1","title":"Task"}],"edges":[]}'
                                )
                            }
                        }
                    ]
                }

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            captured["args"] = args
            captured["kwargs"] = kwargs
            return FakeResponse()

        client = AgentClient(
            api_key="test-key",
            model="test-model",
            mock_mode=False,
            http_post=fake_post,
        )

        proposal = client.complete_json("build a graph")

        self.assertEqual(proposal["nodes"][0]["title"], "Task")
        payload = captured["kwargs"]["json"]
        assert isinstance(payload, dict)
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_client_parses_responses_json_response(self) -> None:
        captured: dict[str, object] = {}

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {
                    "output": [
                        {
                            "content": [
                                {
                                    "text": '{"nodes":[{"id":"n1","title":"Task"}],"edges":[]}'
                                }
                            ]
                        }
                    ]
                }

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            captured["args"] = args
            captured["kwargs"] = kwargs
            return FakeResponse()

        client = AgentClient(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
            wire_api="responses",
            mock_mode=False,
            http_post=fake_post,
        )

        proposal = client.complete_json("build a graph")

        self.assertEqual(proposal["nodes"][0]["title"], "Task")
        self.assertEqual(captured["args"][0], "https://api.example.com/v1/responses")
        payload = captured["kwargs"]["json"]
        assert isinstance(payload, dict)
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["input"], "build a graph")
        self.assertIn("Return only valid JSON", payload["instructions"])
        self.assertEqual(payload["text"], {"format": {"type": "json_object"}})
        self.assertFalse(payload["background"])
        self.assertFalse(payload["store"])

    def test_client_retries_responses_with_plain_payload_when_output_empty(self) -> None:
        calls: list[dict[str, object]] = []

        class FakeResponse:
            def __init__(self, data: dict[str, object]) -> None:
                self._data = data

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return self._data

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            payload = kwargs["json"]
            assert isinstance(payload, dict)
            calls.append(payload)
            if len(calls) == 1:
                return FakeResponse(
                    {
                        "id": "resp_test",
                        "status": "completed",
                        "output": [],
                    }
                )
            return FakeResponse({"output_text": '{"ok": true}'})

        client = AgentClient(
            api_key="test-key",
            wire_api="responses",
            mock_mode=False,
            http_post=fake_post,
        )

        self.assertEqual(client.test_connection(), "Agent API is reachable.")
        self.assertEqual(len(calls), 2)
        self.assertNotIn("instructions", calls[1])
        self.assertIn("Return only valid JSON", calls[1]["input"])

    def test_client_falls_back_to_responses_stream_when_output_empty(self) -> None:
        stream_flags: list[bool] = []

        class FakeResponse:
            def __init__(
                self,
                data: dict[str, object] | None = None,
                lines: list[str] | None = None,
            ) -> None:
                self._data = data or {}
                self._lines = lines or []

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return self._data

            def iter_lines(self, decode_unicode: bool = False) -> list[str]:
                return self._lines

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            is_stream = bool(kwargs.get("stream"))
            stream_flags.append(is_stream)
            if not is_stream:
                return FakeResponse({"id": "resp_test", "status": "completed", "output": []})
            return FakeResponse(
                lines=[
                    "event: response.output_text.delta",
                    'data: {"type":"response.output_text.delta","delta":"{\\"ok\\":"}',
                    "event: response.output_text.delta",
                    'data: {"type":"response.output_text.delta","delta":" true}"}',
                    "event: response.completed",
                    'data: {"type":"response.completed","response":{"status":"completed"}}',
                ]
            )

        client = AgentClient(
            api_key="test-key",
            wire_api="responses",
            mock_mode=False,
            http_post=fake_post,
        )

        self.assertEqual(client.test_connection(), "Agent API is reachable.")
        self.assertIn(True, stream_flags)

    def test_client_parses_responses_nested_text_value_response(self) -> None:
        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": {
                                        "value": (
                                            '{"nodes":[{"id":"n1","title":"Task"}],'
                                            '"edges":[]}'
                                        )
                                    },
                                }
                            ]
                        }
                    ]
                }

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

        client = AgentClient(
            api_key="test-key",
            wire_api="responses",
            mock_mode=False,
            http_post=fake_post,
        )

        proposal = client.complete_json("build a graph")

        self.assertEqual(proposal["nodes"][0]["title"], "Task")

    def test_client_parses_responses_direct_json_object(self) -> None:
        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"ok": True}

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

        client = AgentClient(
            api_key="test-key",
            wire_api="responses",
            mock_mode=False,
            http_post=fake_post,
        )

        self.assertEqual(client.test_connection(), "Agent API is reachable.")

    def test_client_reports_responses_shape_when_content_missing(self) -> None:
        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {
                    "id": "resp_test",
                    "status": "completed",
                    "output": [{"type": "message", "content": []}],
                }

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

        client = AgentClient(
            api_key="test-key",
            wire_api="responses",
            mock_mode=False,
            http_post=fake_post,
        )

        with self.assertRaisesRegex(
            GraphValidationError,
            "top-level keys: id, status, output; status: completed; "
            "output types: message; output count: 1",
        ):
            client.test_connection()

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
