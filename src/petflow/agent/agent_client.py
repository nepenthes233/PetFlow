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

AGENT_SYSTEM_INSTRUCTIONS = (
    "You are PetFlow's planning agent. Return only valid JSON. "
    "For graph proposals, return an object with nodes and edges arrays."
)


@dataclass(slots=True)
class AgentClient:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    wire_api: str = "chat_completions"
    mock_mode: bool | None = None
    timeout_seconds: float = 30.0
    http_post: HttpPost | None = None

    @classmethod
    def from_environment(cls) -> "AgentClient":
        return cls(
            api_key=os.getenv("PETFLOW_AGENT_API_KEY") or os.getenv("IMAGE_API_KEY"),
            base_url=os.getenv("PETFLOW_AGENT_BASE_URL"),
            model=os.getenv("PETFLOW_AGENT_MODEL"),
            wire_api=os.getenv("PETFLOW_AGENT_WIRE_API", "chat_completions"),
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
            wire_api=settings.wire_api or os.getenv("PETFLOW_AGENT_WIRE_API", "chat_completions"),
            mock_mode=settings.mock_mode or env_mock,
        )

    def complete_json(self, prompt: str) -> dict[str, Any]:
        if self._use_mock():
            return self._mock_response(prompt)
        if self.wire_api == "responses":
            return self._complete_responses_json(prompt)
        return self._complete_chat_json(prompt)

    def test_connection(self) -> str:
        if self._use_mock():
            self._mock_response("connection test")
            return "Mock mode is available."
        prompt = 'Return {"ok": true} as JSON to confirm the API is reachable.'
        if self.wire_api == "responses":
            response = self._complete_responses_json(prompt)
        else:
            response = self._complete_chat_json(prompt)
        if response.get("ok") is True:
            return "Agent API is reachable."
        return "Agent API responded with valid JSON."

    def parse_json(self, content: str) -> dict[str, Any]:
        content = self._normalize_json_content(content)
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
                    "content": AGENT_SYSTEM_INSTRUCTIONS,
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

    def _complete_responses_json(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            return self._mock_response(prompt)
        url = self._responses_url()
        last_missing_content_error: GraphValidationError | None = None
        last_stream_error: GraphValidationError | None = None
        post = self.http_post or requests.post
        payloads = self._responses_payloads(prompt)
        for payload in payloads:
            data = self._post_json(url, payload, post)
            try:
                content = self._extract_responses_content(data)
            except GraphValidationError as exc:
                if not self._should_retry_responses_stream(data):
                    raise
                last_missing_content_error = exc
                continue
            return self.parse_json(content)
        for payload in payloads:
            try:
                content = self._post_responses_stream(url, payload, post)
            except GraphValidationError as exc:
                last_stream_error = exc
                continue
            return self.parse_json(content)
        if last_stream_error is not None:
            raise last_stream_error
        if last_missing_content_error is not None:
            raise last_missing_content_error
        raise GraphValidationError("Agent API response missing response content.")

    def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        post: HttpPost,
    ) -> dict[str, Any]:
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
        if not isinstance(data, dict):
            raise GraphValidationError("Agent API response must be a JSON object.")
        return data

    def _post_responses_stream(
        self,
        url: str,
        payload: dict[str, Any],
        post: HttpPost,
    ) -> str:
        stream_payload = dict(payload)
        stream_payload["stream"] = True
        try:
            response = post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json=stream_payload,
                timeout=self.timeout_seconds,
                stream=True,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise GraphValidationError(f"Agent API request failed: {exc}") from exc

        deltas: list[str] = []
        completed_content: str | None = None
        last_data: dict[str, Any] | None = None
        event_name = ""
        try:
            lines = response.iter_lines(decode_unicode=True)
        except AttributeError as exc:
            raise GraphValidationError("Agent API stream response is not readable.") from exc
        for raw_line in lines:
            if isinstance(raw_line, bytes):
                line = raw_line.decode("utf-8", errors="replace")
            else:
                line = str(raw_line)
            line = line.strip()
            if not line:
                continue
            if line.startswith("event:"):
                event_name = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            payload_text = line[5:].strip()
            if not payload_text or payload_text == "[DONE]":
                continue
            try:
                event_data = json.loads(payload_text)
            except json.JSONDecodeError:
                continue
            if not isinstance(event_data, dict):
                continue
            last_data = event_data
            event_type = str(event_data.get("type") or event_name)
            if event_type.endswith(".delta"):
                delta = event_data.get("delta")
                if isinstance(delta, str):
                    deltas.append(delta)
                continue
            response_data = event_data.get("response")
            if isinstance(response_data, dict):
                try:
                    completed_content = self._extract_responses_content(response_data)
                except GraphValidationError:
                    pass
            json_text = self._find_json_text(event_data)
            if json_text:
                completed_content = json_text
        content = "".join(deltas).strip()
        if content:
            return content
        if completed_content:
            return completed_content
        if last_data is not None:
            summary = self._response_summary(last_data)
            raise GraphValidationError(
                f"Agent API stream response missing response content. {summary}"
            )
        raise GraphValidationError("Agent API stream response missing response content.")

    def _responses_payloads(self, prompt: str) -> list[dict[str, Any]]:
        model = self.model or "gpt-4o-mini"
        return [
            {
                "model": model,
                "instructions": AGENT_SYSTEM_INSTRUCTIONS,
                "input": prompt,
                "text": {"format": {"type": "json_object"}},
                "background": False,
                "store": False,
            },
            {
                "model": model,
                "input": f"{AGENT_SYSTEM_INSTRUCTIONS}\n\n{prompt}",
                "background": False,
                "store": False,
            },
        ]

    def _chat_completions_url(self) -> str:
        base_url = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _responses_url(self) -> str:
        base_url = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        if base_url.endswith("/responses"):
            return base_url
        return f"{base_url}/responses"

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
    def _extract_responses_content(data: dict[str, Any]) -> str:
        error = data.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("code") or error.get("type")
            if isinstance(message, str) and message.strip():
                raise GraphValidationError(f"Agent API returned an error: {message}")

        if AgentClient._looks_like_agent_json(data):
            return json.dumps(data)

        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content_items = item.get("content")
                if not isinstance(content_items, list):
                    continue
                for content_item in content_items:
                    if not isinstance(content_item, dict):
                        continue
                    text = content_item.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
                    if isinstance(text, dict):
                        value = text.get("value")
                        if isinstance(value, str) and value.strip():
                            return value
                    output_text = content_item.get("output_text")
                    if isinstance(output_text, str) and output_text.strip():
                        return output_text

        choices = data.get("choices")
        if isinstance(choices, list):
            try:
                return AgentClient._extract_message_content({"choices": choices})
            except GraphValidationError:
                pass

        json_text = AgentClient._find_json_text(data)
        if json_text:
            return json_text

        summary = AgentClient._response_summary(data)
        raise GraphValidationError(
            f"Agent API response missing response content. {summary}"
        )

    @staticmethod
    def _is_missing_responses_content(data: dict[str, Any]) -> bool:
        if isinstance(data.get("error"), dict):
            return False
        if AgentClient._looks_like_agent_json(data):
            return False
        if AgentClient._find_json_text(data):
            return False
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return False
        return True

    @staticmethod
    def _should_retry_responses_stream(data: dict[str, Any]) -> bool:
        if isinstance(data.get("error"), dict):
            return False
        output = data.get("output")
        if output is None:
            return True
        if isinstance(output, list) and not output:
            return True
        return False

    @staticmethod
    def _normalize_json_content(content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3 and lines[-1].strip().startswith("```"):
                stripped = "\n".join(lines[1:-1]).strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end > start:
            return stripped[start : end + 1]
        return stripped

    @staticmethod
    def _looks_like_agent_json(value: dict[str, Any]) -> bool:
        return any(key in value for key in ("ok", "nodes", "edges"))

    @staticmethod
    def _find_json_text(value: object) -> str | None:
        if isinstance(value, str):
            text = AgentClient._normalize_json_content(value)
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return text
            return None
        if isinstance(value, dict):
            for key in ("output_text", "text", "content", "message", "result", "response"):
                found = AgentClient._find_json_text(value.get(key))
                if found:
                    return found
            for child in value.values():
                found = AgentClient._find_json_text(child)
                if found:
                    return found
        if isinstance(value, list):
            for child in value:
                found = AgentClient._find_json_text(child)
                if found:
                    return found
        return None

    @staticmethod
    def _response_summary(data: dict[str, Any]) -> str:
        keys = ", ".join(str(key) for key in list(data.keys())[:8]) or "<none>"
        parts = [f"top-level keys: {keys}"]
        status = data.get("status")
        if isinstance(status, str) and status:
            parts.append(f"status: {status}")
        incomplete_details = data.get("incomplete_details")
        if isinstance(incomplete_details, dict):
            reason = incomplete_details.get("reason")
            if isinstance(reason, str) and reason:
                parts.append(f"incomplete reason: {reason}")
        output = data.get("output")
        if isinstance(output, list):
            output_types = [
                str(item.get("type"))
                for item in output
                if isinstance(item, dict) and item.get("type")
            ]
            if output_types:
                parts.append(f"output types: {', '.join(output_types[:6])}")
            parts.append(f"output count: {len(output)}")
        return "; ".join(parts)

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
