from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from petflow.domain.enums import EventType


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DomainEvent:
    type: EventType
    source: str = "system"
    timestamp: str = field(default_factory=_utc_now_iso)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DomainEvent":
        return cls(
            type=EventType(data["type"]),
            source=data.get("source", "system"),
            timestamp=data.get("timestamp", _utc_now_iso()),
            payload=dict(data.get("payload", {})),
        )

