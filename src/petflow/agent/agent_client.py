from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentClient:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None

    def complete_json(self, prompt: str) -> dict:
        raise NotImplementedError("LLM integration will be implemented later.")

