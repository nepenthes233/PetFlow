from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from petflow.domain.exceptions import GraphValidationError


@dataclass(slots=True)
class AgentClient:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    mock_mode: bool | None = None

    @classmethod
    def from_environment(cls) -> "AgentClient":
        return cls(
            api_key=os.getenv("PETFLOW_AGENT_API_KEY"),
            base_url=os.getenv("PETFLOW_AGENT_BASE_URL"),
            model=os.getenv("PETFLOW_AGENT_MODEL"),
            mock_mode=os.getenv("PETFLOW_AGENT_MOCK", "").lower() in {"1", "true", "yes"},
        )

    def complete_json(self, prompt: str) -> dict[str, Any]:
        if self._use_mock():
            return self._mock_response(prompt)
        raise NotImplementedError(
            "Real LLM integration is not configured. Set PETFLOW_AGENT_MOCK=1 "
            "or leave PETFLOW_AGENT_API_KEY unset for demo mock mode."
        )

    def parse_json(self, content: str) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise GraphValidationError("Agent response is not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise GraphValidationError("Agent response must be a JSON object.")
        return parsed

    def _use_mock(self) -> bool:
        if self.mock_mode is not None:
            return self.mock_mode
        return not self.api_key

    @staticmethod
    def _mock_response(prompt: str) -> dict[str, Any]:
        if "拆分" in prompt or "split" in prompt.lower():
            return {
                "nodes": [
                    {
                        "id": "split_1",
                        "type": "task",
                        "title": "Clarify acceptance criteria",
                        "priority": 4,
                        "estimated_minutes": 25,
                        "x": 160,
                        "y": 260,
                    },
                    {
                        "id": "split_2",
                        "type": "task",
                        "title": "Implement the smallest working slice",
                        "priority": 5,
                        "estimated_minutes": 60,
                        "x": 380,
                        "y": 260,
                    },
                    {
                        "id": "split_3",
                        "type": "checkpoint",
                        "title": "Review and test the result",
                        "priority": 4,
                        "estimated_minutes": 30,
                        "x": 600,
                        "y": 260,
                    },
                ],
                "edges": [
                    {
                        "source": "split_1",
                        "target": "split_2",
                        "type": "dependency",
                    },
                    {
                        "source": "split_2",
                        "target": "split_3",
                        "type": "dependency",
                    },
                ],
            }
        return {
            "nodes": [
                {
                    "id": "goal_1",
                    "type": "task",
                    "title": "Define the goal",
                    "priority": 5,
                    "estimated_minutes": 30,
                    "x": 120,
                    "y": 160,
                },
                {
                    "id": "goal_2",
                    "type": "task",
                    "title": "Build the core workflow",
                    "priority": 5,
                    "estimated_minutes": 90,
                    "x": 360,
                    "y": 160,
                },
                {
                    "id": "goal_3",
                    "type": "checkpoint",
                    "title": "Prepare demo and report",
                    "priority": 4,
                    "estimated_minutes": 60,
                    "x": 600,
                    "y": 160,
                },
            ],
            "edges": [
                {"source": "goal_1", "target": "goal_2", "type": "dependency"},
                {"source": "goal_2", "target": "goal_3", "type": "dependency"},
            ],
        }
