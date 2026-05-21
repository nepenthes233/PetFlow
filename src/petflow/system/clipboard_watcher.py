from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(slots=True)
class ClipboardCapture:
    title: str
    content: str
    resource_type: str


class ClipboardWatcher:
    def __init__(self) -> None:
        self.active = False

    def start(self) -> None:
        self.active = True

    def stop(self) -> None:
        self.active = False

    def capture_once(self, read_clipboard: Callable[[], str]) -> ClipboardCapture | None:
        try:
            content = read_clipboard().strip()
        except Exception:
            return None
        if not content:
            return None
        resource_type = "url" if self._is_url(content) else "text"
        return ClipboardCapture(
            title=self._title_for(content, resource_type),
            content=content,
            resource_type=resource_type,
        )

    @staticmethod
    def _is_url(content: str) -> bool:
        parsed = urlparse(content)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def _title_for(content: str, resource_type: str) -> str:
        if resource_type == "url":
            parsed = urlparse(content)
            return parsed.netloc or "Clipboard URL"
        first_line = content.splitlines()[0].strip()
        if len(first_line) > 42:
            return first_line[:41] + "..."
        return first_line or "Clipboard Text"
