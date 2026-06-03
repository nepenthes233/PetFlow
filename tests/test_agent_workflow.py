from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from petflow.agent.agent_client import AgentClient
from petflow.agent.agent_executor import AgentExecutor
from petflow.agent.proposal import AgentProposalValidator
from petflow.app import AppContext
from petflow.domain import EdgeType, GraphValidationError, NodeType
from petflow.domain.enums import RepeatType


class AgentWorkflowTest(unittest.TestCase):
    def test_original_agent_contract_remains_applicable_without_new_fields(self) -> None:
        context = AppContext.create()
        original_contract_proposal = {
            "nodes": [
                {
                    "id": "n1",
                    "type": "task",
                    "title": "Plan",
                    "description": "Outline work",
                    "priority": 5,
                    "estimated_minutes": 45,
                    "x": 120,
                    "y": 120,
                },
                {
                    "id": "n2",
                    "type": "task",
                    "title": "Build",
                    "description": "",
                    "priority": 3,
                    "estimated_minutes": 90,
                    "x": 330,
                    "y": 120,
                },
            ],
            "edges": [
                {
                    "source": "n1",
                    "target": "n2",
                    "type": "dependency",
                    "label": "then",
                }
            ],
        }

        created = AgentExecutor(context.graph_service).apply_graph_proposal(
            original_contract_proposal
        )

        self.assertEqual([node.title for node in created], ["Plan", "Build"])
        self.assertEqual(created[0].repeat_type, RepeatType.NONE)
        self.assertIsNone(created[0].next_due_at)
        self.assertEqual(len(context.graph.edges), 1)

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

    def test_validator_accepts_optional_schedule_fields(self) -> None:
        proposal = AgentProposalValidator().validate(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "title": "Review",
                        "repeat_type": "weekly",
                        "repeat_interval": 2,
                        "next_due_at": "2026-05-27",
                    }
                ],
                "edges": [],
            }
        )

        node = proposal["nodes"][0]
        self.assertEqual(node["repeat_type"], "weekly")
        self.assertEqual(node["repeat_interval"], 2)
        self.assertEqual(node["next_due_at"], "2026-05-27")

    def test_validator_normalizes_deadline_and_nested_routine_fields(self) -> None:
        proposal = AgentProposalValidator().validate(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "title": "Feed cats",
                        "deadline": "2026-06-02",
                        "routine": {
                            "recurrence": "daily",
                            "interval_days": 1,
                            "streak": 2,
                        },
                        "tags": "home, pets, home",
                        "checklist": [{"item": "Prepare food"}, "Refill water"],
                    }
                ],
                "edges": [],
            }
        )

        node = proposal["nodes"][0]
        self.assertEqual(node["type"], "routine")
        self.assertEqual(node["repeat_type"], "daily")
        self.assertEqual(node["repeat_interval"], 1)
        self.assertEqual(node["next_due_at"], "2026-06-02")
        self.assertEqual(node["streak"], 2)
        self.assertEqual(node["tags"], ["home", "pets"])
        self.assertEqual(node["checklist"], ["Prepare food", "Refill water"])

    def test_validator_accepts_delete_and_layout_actions(self) -> None:
        proposal = AgentProposalValidator().validate(
            {
                "nodes": [],
                "edges": [],
                "delete_nodes": [{"id": "node_1"}, "node_2", "node_1"],
                "delete_all_nodes": "false",
                "layout": {"enabled": True, "strategy": "grid"},
            }
        )

        self.assertEqual(proposal["delete_node_ids"], ["node_1", "node_2"])
        self.assertFalse(proposal["delete_all_nodes"])
        self.assertEqual(proposal["layout"], {"enabled": True, "strategy": "grid"})

    def test_validator_accepts_delete_all_action(self) -> None:
        proposal = AgentProposalValidator().validate(
            {
                "nodes": [],
                "edges": [],
                "clear_graph": True,
                "delete_query": "feed cats",
            }
        )

        self.assertTrue(proposal["delete_all_nodes"])
        self.assertEqual(proposal["delete_query"], "feed cats")

    def test_validator_accepts_update_and_add_edge_actions(self) -> None:
        proposal = AgentProposalValidator().validate(
            {
                "nodes": [],
                "edges": [],
                "update_nodes": [
                    {
                        "query": "feed cats",
                        "status": "done",
                        "deadline": "2026-06-04",
                        "routine": {"recurrence": "weekly", "interval_days": 2},
                        "name": "Feed cats weekly",
                    }
                ],
                "add_edges": [
                    {
                        "source_query": "buy food",
                        "target_query": "feed cats",
                        "type": "dependency",
                        "label": "then",
                    }
                ],
            }
        )

        update = proposal["update_nodes"][0]
        self.assertEqual(update["query"], "feed cats")
        self.assertEqual(update["changes"]["title"], "Feed cats weekly")
        self.assertEqual(update["changes"]["status"].value, "done")
        self.assertEqual(update["changes"]["next_due_at"], "2026-06-04")
        self.assertEqual(update["changes"]["repeat_type"].value, "weekly")
        self.assertEqual(update["changes"]["repeat_interval"], 2)
        edge = proposal["add_edges"][0]
        self.assertEqual(edge["source_query"], "buy food")
        self.assertEqual(edge["target_query"], "feed cats")

    def test_validator_normalizes_common_model_status_and_priority_aliases(self) -> None:
        proposal = AgentProposalValidator().validate(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "title": "Draft slides",
                        "status": "pending",
                        "priority": "high",
                    },
                    {
                        "id": "n2",
                        "title": "Present",
                        "status": "in progress",
                        "priority": "urgent",
                    },
                ],
                "edges": [],
            }
        )

        self.assertEqual(proposal["nodes"][0]["status"], "todo")
        self.assertEqual(proposal["nodes"][0]["priority"], 4)
        self.assertEqual(proposal["nodes"][1]["status"], "doing")
        self.assertEqual(proposal["nodes"][1]["priority"], 5)

    def test_validator_reports_invalid_numeric_value_without_value_error(self) -> None:
        with self.assertRaisesRegex(
            GraphValidationError, "estimated_minutes must be a number"
        ):
            AgentProposalValidator().validate(
                {
                    "nodes": [
                        {"id": "n1", "title": "Draft slides", "estimated_minutes": "soon"}
                    ],
                    "edges": [],
                }
            )

    def test_validator_rejects_invalid_schedule_date(self) -> None:
        with self.assertRaises(GraphValidationError):
            AgentProposalValidator().validate(
                {
                    "nodes": [{"id": "n1", "title": "Review", "next_due_at": "soon"}],
                    "edges": [],
                }
            )

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

    def test_default_validator_accepts_larger_proposals(self) -> None:
        proposal = AgentProposalValidator().validate(
            {
                "nodes": [
                    {"id": f"node_{index}", "title": f"Task {index}"}
                    for index in range(1, 19)
                ],
                "edges": [],
            }
        )

        self.assertEqual(len(proposal["nodes"]), 18)

    def test_mock_client_returns_graph_proposal(self) -> None:
        client = AgentClient(mock_mode=True)

        proposal = client.complete_json("generate a graph")

        self.assertIn("nodes", proposal)
        self.assertIn("edges", proposal)

    def test_mock_client_answers_companion_chat(self) -> None:
        client = AgentClient(mock_mode=True)

        response = client.complete_json(
            "Return only a JSON object with a single `reply` string field."
        )

        self.assertIn("reply", response)
        self.assertNotIn("nodes", response)

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

    def test_deepseek_connection_test_uses_required_url_headers_and_model(self) -> None:
        captured: dict[str, object] = {}

        class FakeResponse:
            status_code = 200

            def json(self) -> dict[str, object]:
                return {"choices": [{"message": {"content": '{"ok": true}'}}]}

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            captured["args"] = args
            captured["kwargs"] = kwargs
            return FakeResponse()

        client = AgentClient(
            api_key="  sk-secret-last  ",
            base_url=" https://api.deepseek.com/ ",
            model="deepseek-chat",
            mock_mode=False,
            http_post=fake_post,
        )

        self.assertEqual(client.test_connection(), "Agent API is reachable.")
        self.assertEqual(
            captured["args"][0], "https://api.deepseek.com/chat/completions"
        )
        kwargs = captured["kwargs"]
        assert isinstance(kwargs, dict)
        self.assertEqual(
            kwargs["headers"],
            {
                "Authorization": "Bearer sk-secret-last",
                "Content-Type": "application/json",
            },
        )
        payload = kwargs["json"]
        assert isinstance(payload, dict)
        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertNotIn("api_key", payload)
        self.assertNotIn("sk-secret-last", str(payload))

    def test_deepseek_http_error_includes_body_and_masked_key_only(self) -> None:
        class FakeResponse:
            status_code = 401
            text = '{"error":{"message":"Authentication Fails"}}'

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

        client = AgentClient(
            api_key="sk-secret-abcd",
            base_url="https://api.deepseek.com",
            mock_mode=False,
            http_post=fake_post,
        )

        with self.assertRaises(GraphValidationError) as caught:
            client.test_connection()

        message = str(caught.exception)
        self.assertIn("HTTP 401", message)
        self.assertIn("Authentication Fails", message)
        self.assertIn("sk-****abcd", message)
        self.assertNotIn("sk-secret-abcd", message)

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
                lines: list[bytes] | None = None,
            ) -> None:
                self._data = data or {}
                self._lines = lines or []

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return self._data

            def iter_lines(self, decode_unicode: bool = False) -> list[bytes]:
                self.decode_unicode = decode_unicode
                return self._lines

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            is_stream = bool(kwargs.get("stream"))
            stream_flags.append(is_stream)
            if not is_stream:
                return FakeResponse({"id": "resp_test", "status": "completed", "output": []})
            return FakeResponse(
                lines=[
                    b"event: response.output_text.delta",
                    b'data: {"type":"response.output_text.delta","delta":"{\\"ok\\":"}',
                    b"event: response.output_text.delta",
                    b'data: {"type":"response.output_text.delta","delta":" true}"}',
                    b"event: response.completed",
                    b'data: {"type":"response.completed","response":{"status":"completed"}}',
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

    def test_client_decodes_responses_stream_as_utf8(self) -> None:
        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"id": "resp_test", "status": "completed", "output": []}

            def iter_lines(self, decode_unicode: bool = False) -> list[bytes]:
                self.decode_unicode = decode_unicode
                event = (
                    'data: {"type":"response.output_text.delta",'
                    '"delta":"{\\"summary\\": \\"下一步\\", \\"highlights\\": []}"}'
                )
                return [b"event: response.output_text.delta", event.encode("utf-8")]

        responses = [FakeResponse(), FakeResponse(), FakeResponse()]

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            return responses.pop(0)

        client = AgentClient(
            api_key="test-key",
            wire_api="responses",
            mock_mode=False,
            http_post=fake_post,
        )

        response = client.complete_json("review")

        self.assertEqual(response["summary"], "下一步")

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
        self.assertEqual(
            next(iter(context.graph.edges.values())).type,
            EdgeType.DEPENDENCY,
        )
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

    def test_executor_applies_optional_schedule_fields(self) -> None:
        context = AppContext.create()
        created = AgentExecutor(context.graph_service).apply_graph_proposal(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "title": "Weekly review",
                        "repeat_type": "weekly",
                        "repeat_interval": 2,
                        "next_due_at": "2026-05-27",
                    }
                ],
                "edges": [],
            }
        )

        self.assertEqual(created[0].repeat_type, RepeatType.WEEKLY)
        self.assertEqual(created[0].repeat_interval, 2)
        self.assertEqual(created[0].next_due_at, "2026-05-27")

    def test_executor_applies_agent_node_detail_fields(self) -> None:
        context = AppContext.create()
        created = AgentExecutor(context.graph_service).apply_graph_proposal(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "title": "Morning care",
                        "deadline": "2026-06-03",
                        "routine": {"recurrence": "daily", "interval_days": 1},
                        "actual_minutes": 5,
                        "tags": ["pet", "morning"],
                        "resource_type": "text",
                        "resource_path": "feeding notes",
                        "checklist": ["food", "water"],
                    }
                ],
                "edges": [],
            }
        )

        node = created[0]
        self.assertEqual(node.type, NodeType.ROUTINE)
        self.assertEqual(node.next_due_at, "2026-06-03")
        self.assertEqual(node.repeat_type, RepeatType.DAILY)
        self.assertEqual(node.actual_minutes, 5)
        self.assertEqual(node.tags, ["pet", "morning"])
        self.assertEqual(node.resource_type.value, "text")
        self.assertEqual(node.resource_path, "feeding notes")
        self.assertEqual([item.text for item in node.checklist], ["food", "water"])

    def test_executor_deletes_nodes_from_agent_proposal(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(title="Keep")
        second = context.graph_service.create_node(title="Delete")
        context.graph_service.create_edge(first.id, second.id, EdgeType.DEPENDENCY)
        executor = AgentExecutor(context.graph_service)

        created = executor.apply_graph_proposal(
            {
                "nodes": [],
                "edges": [],
                "delete_node_ids": [second.id],
            }
        )

        self.assertEqual(created, [])
        self.assertIn(first.id, context.graph.nodes)
        self.assertNotIn(second.id, context.graph.nodes)
        self.assertFalse(context.graph.edges)
        self.assertEqual(executor.last_deleted_node_ids, [second.id])

    def test_executor_deletes_all_nodes_from_agent_proposal(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(title="First")
        second = context.graph_service.create_node(title="Second")
        context.graph_service.create_edge(first.id, second.id, EdgeType.DEPENDENCY)
        context.graph_service.set_current_node(first.id)
        executor = AgentExecutor(context.graph_service)

        executor.apply_graph_proposal(
            {
                "nodes": [],
                "edges": [],
                "delete_all_nodes": True,
            }
        )

        self.assertFalse(context.graph.nodes)
        self.assertFalse(context.graph.edges)
        self.assertEqual(set(executor.last_deleted_node_ids), {first.id, second.id})
        self.assertIsNone(context.graph.workspace.current_node_id)

    def test_executor_deletes_nodes_by_query(self) -> None:
        context = AppContext.create()
        keep = context.graph_service.create_node(title="Buy food")
        delete = context.graph_service.create_node(
            title="Feed cats",
            description="Morning pet routine",
            tags=["pets"],
        )
        executor = AgentExecutor(context.graph_service)

        executor.apply_graph_proposal(
            {
                "nodes": [],
                "edges": [],
                "delete_query": "cats pets",
            }
        )

        self.assertIn(keep.id, context.graph.nodes)
        self.assertNotIn(delete.id, context.graph.nodes)
        self.assertEqual(executor.last_deleted_node_ids, [delete.id])

    def test_executor_reports_delete_query_without_matches(self) -> None:
        context = AppContext.create()
        context.graph_service.create_node(title="Keep")

        with self.assertRaises(GraphValidationError):
            AgentExecutor(context.graph_service).apply_graph_proposal(
                {
                    "nodes": [],
                    "edges": [],
                    "delete_query": "missing target",
                }
            )

    def test_executor_updates_nodes_by_query(self) -> None:
        context = AppContext.create()
        node = context.graph_service.create_node(title="Feed cats")

        AgentExecutor(context.graph_service).apply_graph_proposal(
            {
                "nodes": [],
                "edges": [],
                "update_nodes": [
                    {
                        "query": "feed cats",
                        "status": "doing",
                        "deadline": "2026-06-04",
                        "name": "Feed cats weekly",
                        "routine": {"recurrence": "weekly", "interval_days": 2},
                    }
                ],
            }
        )

        self.assertEqual(node.title, "Feed cats weekly")
        self.assertEqual(node.status.value, "doing")
        self.assertEqual(node.next_due_at, "2026-06-04")
        self.assertEqual(node.repeat_type, RepeatType.WEEKLY)
        self.assertEqual(node.repeat_interval, 2)

    def test_executor_adds_edges_by_query(self) -> None:
        context = AppContext.create()
        source = context.graph_service.create_node(title="Buy food")
        target = context.graph_service.create_node(title="Feed cats")
        executor = AgentExecutor(context.graph_service)

        executor.apply_graph_proposal(
            {
                "nodes": [],
                "edges": [],
                "add_edges": [
                    {
                        "source_query": "buy food",
                        "target_query": "feed cats",
                        "type": "dependency",
                        "label": "then",
                    }
                ],
            }
        )

        edge = next(iter(context.graph.edges.values()))
        self.assertEqual(edge.source, source.id)
        self.assertEqual(edge.target, target.id)
        self.assertEqual(edge.label, "then")
        self.assertEqual(executor.last_added_edge_ids, [edge.id])

    def test_executor_applies_requested_layout(self) -> None:
        context = AppContext.create()
        first = context.graph_service.create_node(title="First", x=900, y=900)
        second = context.graph_service.create_node(title="Second", x=900, y=900)
        executor = AgentExecutor(context.graph_service)

        executor.apply_graph_proposal(
            {
                "nodes": [],
                "edges": [],
                "layout": {"enabled": True},
            }
        )

        self.assertTrue(executor.last_layout_requested)
        self.assertEqual((first.x, first.y), (120.0, 120.0))
        self.assertGreater(second.x, first.x)


if __name__ == "__main__":
    unittest.main()
