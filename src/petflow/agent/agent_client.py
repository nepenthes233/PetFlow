from __future__ import annotations

import json
import os
import re
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

    def __post_init__(self) -> None:
        self.api_key = self.api_key.strip() if self.api_key else None
        self.base_url = self.base_url.strip().rstrip("/") if self.base_url else None
        self.model = self.model.strip() if self.model else None
        self.wire_api = self.wire_api.strip()

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
        settings_key = settings.api_key.strip()
        environment_key = (
            os.getenv("PETFLOW_AGENT_API_KEY", "").strip()
            or os.getenv("IMAGE_API_KEY", "").strip()
        )
        return cls(
            api_key=settings_key or environment_key or None,
            base_url=(
                settings.base_url.strip()
                or os.getenv("PETFLOW_AGENT_BASE_URL", "").strip()
                or None
            ),
            model=(
                settings.model.strip()
                or os.getenv("PETFLOW_AGENT_MODEL", "").strip()
                or None
            ),
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
            test_model = "deepseek-v4-flash" if self._is_deepseek() else None
            response = self._complete_chat_json(prompt, model_override=test_model)
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

    def _complete_chat_json(
        self, prompt: str, model_override: str | None = None
    ) -> dict[str, Any]:
        if not self.api_key:
            return self._mock_response(prompt)
        url = self._chat_completions_url()
        payload = {
            "model": model_override or self.model or "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": AGENT_SYSTEM_INSTRUCTIONS,
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 4096,
        }
        post = self.http_post or requests.post
        try:
            response = post(
                url,
                headers=self._json_headers(),
                json=payload,
                timeout=self.timeout_seconds,
            )
            self._ensure_success(response, url)
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
                headers=self._json_headers(),
                json=payload,
                timeout=self.timeout_seconds,
            )
            self._ensure_success(response, url)
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
                    **self._json_headers(),
                    "Accept": "text/event-stream",
                },
                json=stream_payload,
                timeout=self.timeout_seconds,
                stream=True,
            )
            self._ensure_success(response, url)
        except requests.RequestException as exc:
            raise GraphValidationError(f"Agent API request failed: {exc}") from exc

        deltas: list[str] = []
        completed_content: str | None = None
        last_data: dict[str, Any] | None = None
        event_name = ""
        try:
            lines = response.iter_lines(decode_unicode=False)
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
        if base_url.lower() in {
            "https://api.deepseek.com",
            "https://api.deepseek.com/v1",
        }:
            return "https://api.deepseek.com/chat/completions"
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _responses_url(self) -> str:
        base_url = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        if base_url.endswith("/responses"):
            return base_url
        return f"{base_url}/responses"

    def _json_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key or ''}",
            "Content-Type": "application/json",
        }

    def _is_deepseek(self) -> bool:
        base_url = (self.base_url or "").lower().rstrip("/")
        return base_url in {
            "https://api.deepseek.com",
            "https://api.deepseek.com/v1",
        }

    def _ensure_success(self, response: object, url: str) -> None:
        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int) and not 200 <= status_code < 300:
            body = self._response_body(response)
            raise GraphValidationError(
                f"Agent API returned HTTP {status_code} from {url} "
                f"(key {self.masked_api_key()}). Response body: {body}"
            )
        if status_code is None:
            response.raise_for_status()

    def _response_body(self, response: object) -> str:
        text = getattr(response, "text", "")
        if not isinstance(text, str) or not text.strip():
            try:
                text = json.dumps(response.json(), ensure_ascii=False)
            except (AttributeError, ValueError, TypeError):
                text = "<empty response body>"
        key = self.api_key or ""
        return text.replace(key, self.masked_api_key()) if key else text

    def masked_api_key(self) -> str:
        key = self.api_key or ""
        suffix = key[-4:] if len(key) >= 4 else "****"
        return f"sk-****{suffix}"

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
        if "`reply` string field" in prompt:
            return {
                "reply": (
                    "I can answer questions here. Use Plan Flow when you want "
                    "me to create task nodes and relationships."
                )
            }
        lowered = prompt.lower()
        action_text = lowered
        for marker in ("user message:", "user goal:"):
            if marker in lowered:
                action_text = lowered.rsplit(marker, 1)[-1]
                break
        if any(
            phrase in action_text
            for phrase in (
                "delete all",
                "remove all",
                "clear graph",
                "clear canvas",
                "删除全部",
                "全部删除",
                "清空",
            )
        ):
            return {
                "nodes": [],
                "edges": [],
                "delete_node_ids": [],
                "delete_all_nodes": True,
                "layout": {"enabled": False, "strategy": "flow"},
            }
        existing_ids = re.findall(r"^- ([^:\n]+):", prompt, flags=re.MULTILINE)
        if any(
            word in action_text for word in ("complete", "done", "finish", "完成")
        ):
            return {
                "nodes": [],
                "edges": [],
                "update_nodes": [
                    {
                        "id": existing_ids[0] if existing_ids else "",
                        "query": "" if existing_ids else action_text,
                        "status": "done",
                    }
                ],
            }
        if any(word in action_text for word in ("connect", "link", "depend", "连接")):
            return {
                "nodes": [],
                "edges": [],
                "add_edges": [
                    {
                        "source": existing_ids[0] if len(existing_ids) >= 1 else "",
                        "target": existing_ids[1] if len(existing_ids) >= 2 else "",
                        "source_query": "" if len(existing_ids) >= 1 else action_text,
                        "target_query": "" if len(existing_ids) >= 2 else action_text,
                        "type": "dependency",
                    }
                ],
            }
        if any(
            word in action_text for word in ("arrange", "organize", "layout", "整理")
        ):
            return {
                "nodes": [],
                "edges": [],
                "delete_node_ids": [],
                "layout": {"enabled": True, "strategy": "flow"},
            }
        if any(word in action_text for word in ("delete", "remove", "删除")):
            delete_query = re.sub(
                r"\b(delete|remove|node|task)\b|删除|节点|任务",
                " ",
                action_text,
            ).strip()
            if not delete_query:
                delete_query = existing_ids[0] if existing_ids else ""
            return {
                "nodes": [],
                "edges": [],
                "delete_node_ids": [],
                "delete_query": delete_query,
                "layout": {"enabled": True, "strategy": "flow"},
            }
        if "拆分" in prompt or "split" in lowered:
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
        due_match = re.search(r"\d{4}-\d{2}-\d{2}", action_text)
        due_value = due_match.group(0) if due_match else None
        routine_requested = any(
            word in action_text
            for word in (
                "routine",
                "repeat",
                "daily",
                "weekly",
                "monthly",
                "每天",
                "每周",
            )
        )
        first_title = "Set up the routine" if routine_requested else "Define the goal"
        return {
            "nodes": [
                {
                    "id": "goal_1",
                    "type": "routine" if routine_requested else "task",
                    "title": first_title,
                    "priority": 5,
                    "estimated_minutes": 30,
                    "repeat_type": "daily" if routine_requested else "none",
                    "repeat_interval": 1,
                    "next_due_at": due_value,
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
