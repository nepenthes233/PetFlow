from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from petflow.config import DEFAULT_SETTINGS_PATH
from petflow.domain.exceptions import RepositoryError


@dataclass(slots=True)
class AgentSettings:
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    wire_api: str = "chat_completions"
    mock_mode: bool = False

    def __post_init__(self) -> None:
        self.api_key = self.api_key.strip()
        self.base_url = self.base_url.strip().rstrip("/")
        self.model = self.model.strip()
        self.wire_api = self.wire_api.strip()

    @classmethod
    def load(cls, path: str | Path = DEFAULT_SETTINGS_PATH) -> "AgentSettings":
        file_path = Path(path)
        if not file_path.exists():
            return cls()
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RepositoryError(f"Failed to load settings: {file_path}") from exc
        if not isinstance(data, dict):
            raise RepositoryError(f"Settings file must contain an object: {file_path}")
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentSettings":
        return cls(
            api_key=str(data.get("api_key", "")),
            base_url=str(data.get("base_url", "https://api.openai.com/v1")),
            model=str(data.get("model", "gpt-4o-mini")),
            wire_api=str(data.get("wire_api", "chat_completions")),
            mock_mode=bool(data.get("mock_mode", False)),
        )

    def save(self, path: str | Path = DEFAULT_SETTINGS_PATH) -> None:
        file_path = Path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise RepositoryError(f"Failed to save settings: {file_path}") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "wire_api": self.wire_api,
            "mock_mode": self.mock_mode,
        }
