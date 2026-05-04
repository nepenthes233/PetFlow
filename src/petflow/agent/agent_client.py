from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests

from petflow.agent.settings import AgentSettings
from petflow.domain.exceptions import GraphValidationError

HttpPost = Callable[..., object]


@dataclass(slots=True)
class AgentClient:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    mock_mode: bool | None = None
    timeout_seconds: float = 30.0
    http_post: HttpPost | None = None

    @classmethod
    def from_environment(cls) -> "AgentClient":
        return cls(
            api_key=os.getenv("PETFLOW_AGENT_API_KEY") or os.getenv("IMAGE_API_KEY"),
            base_url=os.getenv("PETFLOW_AGENT_BASE_URL"),
            model=os.getenv("PETFLOW_AGENT_MODEL"),
            mock_mode=os.getenv("PETFLOW_AGENT_MOCK", "").lower() in {"1", "true", "yes"},
        )

    @classmethod
    def from_settings(cls, settings: AgentSettings | None = None) -> "AgentClient":
        settings = settings or AgentSettings.load()
        env_mock = os.getenv("PETFLOW_AGENT_MOCK", "").lower() in {"1", "true", "yes"}
        return cls(
            api_key=(
                settings.api_key
                or os.getenv("PETFLOW_AGENT_API_KEY")
                or os.getenv("IMAGE_API_KEY")
            ),
            base_url=settings.base_url or os.getenv("PETFLOW_AGENT_BASE_URL"),
            model=settings.model or os.getenv("PETFLOW_AGENT_MODEL"),
            mock_mode=settings.mock_mode or env_mock,
        )

    def complete_json(self, prompt: str) -> dict[str, Any]:
        if self._use_mock():
            return self._mock_response(prompt)
        return self._complete_chat_json(prompt)

    def test_connection(self) -> str:
        if self._use_mock():
            self._mock_response("connection test")
            return "Mock mode is available."
        response = self._complete_chat_json(
            'Return {"ok": true} as JSON to confirm the API is reachable.'
        )
        if response.get("ok") is True:
            return "Agent API is reachable."
        return "Agent API responded with valid JSON."

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

    def _complete_chat_json(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            return self._mock_response(prompt)
        url = self._chat_completions_url()
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are PetFlow's planning agent. Return only valid JSON. "
                        "For graph proposals, return an object with nodes and edges arrays."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        post = self.http_post or requests.post
        try:
            response = post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise GraphValidationError(f"Agent API request failed: {exc}") from exc
        except ValueError as exc:
            raise GraphValidationError("Agent API response is not valid JSON.") from exc
        content = self._extract_message_content(data)
        return self.parse_json(content)

    def _chat_completions_url(self) -> str:
        base_url = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    @staticmethod
    def _extract_message_content(data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GraphValidationError("Agent API response missing message content.") from exc
        if not isinstance(content, str) or not content.strip():
            raise GraphValidationError("Agent API response content is empty.")
        return content

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
