from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from petflow.domain.enums import (
    EdgeType,
    NodeStatus,
    NodeType,
    PetStateType,
    RepeatType,
    ResourceType,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_enum(enum_cls: type[Enum], value: Any, default: Enum) -> Enum:
    if isinstance(value, enum_cls):
        return value
    if value is None:
        return default
    try:
        return enum_cls(value)
    except ValueError:
        return default


@dataclass(slots=True)
class ChecklistItem:
    id: str
    text: str
    checked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "text": self.text, "checked": self.checked}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChecklistItem":
        return cls(
            id=data.get("id", data.get("text", "")),
            text=data.get("text", ""),
            checked=bool(data.get("checked", False)),
        )


@dataclass(slots=True)
class ProjectMetadata:
    name: str = "PetFlow"
    description: str = ""
    schema_version: int = 1
    created_at: str | None = None
    updated_at: str | None = None
    tags: list[str] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = _utc_now_iso()
        if self.created_at is None:
            self.created_at = self.updated_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectMetadata":
        return cls(
            name=data.get("name", "PetFlow"),
            description=data.get("description", ""),
            schema_version=int(data.get("schema_version", 1)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            tags=list(data.get("tags", [])),
        )


@dataclass(slots=True)
class PetState:
    current_node_id: str | None = None
    state: PetStateType = PetStateType.IDLE
    x: float = 0.0
    y: float = 0.0
    mood: str = "neutral"
    speech: str = ""
    visible: bool = True
    last_updated_at: str | None = None

    def touch(self) -> None:
        self.last_updated_at = _utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_node_id": self.current_node_id,
            "state": self.state.value,
            "x": self.x,
            "y": self.y,
            "mood": self.mood,
            "speech": self.speech,
            "visible": self.visible,
            "last_updated_at": self.last_updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PetState":
        return cls(
            current_node_id=data.get("current_node_id"),
            state=_coerce_enum(PetStateType, data.get("state"), PetStateType.IDLE),
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            mood=data.get("mood", "neutral"),
            speech=data.get("speech", ""),
            visible=bool(data.get("visible", True)),
            last_updated_at=data.get("last_updated_at"),
        )


@dataclass(slots=True)
class WorkspaceState:
    current_node_id: str | None = None
    selected_node_ids: list[str] = field(default_factory=list)
    selected_edge_ids: list[str] = field(default_factory=list)
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    active_panel: str = "graph"
    focus_mode: bool = False
    theme: str = "light"

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_node_id": self.current_node_id,
            "selected_node_ids": list(self.selected_node_ids),
            "selected_edge_ids": list(self.selected_edge_ids),
            "zoom": self.zoom,
            "pan_x": self.pan_x,
            "pan_y": self.pan_y,
            "active_panel": self.active_panel,
            "focus_mode": self.focus_mode,
            "theme": self.theme,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceState":
        return cls(
            current_node_id=data.get("current_node_id"),
            selected_node_ids=list(data.get("selected_node_ids", [])),
            selected_edge_ids=list(data.get("selected_edge_ids", [])),
            zoom=float(data.get("zoom", 1.0)),
            pan_x=float(data.get("pan_x", 0.0)),
            pan_y=float(data.get("pan_y", 0.0)),
            active_panel=data.get("active_panel", "graph"),
            focus_mode=bool(data.get("focus_mode", False)),
            theme=data.get("theme", "light"),
        )


@dataclass(slots=True)
class Node:
    id: str
    type: NodeType
    title: str
    description: str = ""
    status: NodeStatus = NodeStatus.TODO
    priority: int = 3
    estimated_minutes: int = 30
    actual_minutes: int = 0
    x: float = 100.0
    y: float = 100.0
    parent_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    tags: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    repeat_type: RepeatType = RepeatType.NONE
    repeat_days: list[int] = field(default_factory=list)
    repeat_interval: int = 1
    last_completed_at: str | None = None
    next_due_at: str | None = None
    streak: int = 0
    resource_type: ResourceType = ResourceType.URL
    resource_path: str = ""
    checklist: list[ChecklistItem] = field(default_factory=list)
    unlock_condition: str = ""
    duration_minutes: int = 0
    locked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = _utc_now_iso()
        if self.created_at is None:
            self.created_at = self.updated_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "estimated_minutes": self.estimated_minutes,
            "actual_minutes": self.actual_minutes,
            "x": self.x,
            "y": self.y,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "tags": list(self.tags),
            "attachments": list(self.attachments),
            "repeat_type": self.repeat_type.value,
            "repeat_days": list(self.repeat_days),
            "repeat_interval": self.repeat_interval,
            "last_completed_at": self.last_completed_at,
            "next_due_at": self.next_due_at,
            "streak": self.streak,
            "resource_type": self.resource_type.value,
            "resource_path": self.resource_path,
            "checklist": [item.to_dict() for item in self.checklist],
            "unlock_condition": self.unlock_condition,
            "duration_minutes": self.duration_minutes,
            "locked": self.locked,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        legacy_routine = data.get("routine")
        if not isinstance(legacy_routine, dict):
            legacy_routine = {}
        return cls(
            id=data["id"],
            type=_coerce_enum(NodeType, data.get("type"), NodeType.TASK),
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=_coerce_enum(NodeStatus, data.get("status"), NodeStatus.TODO),
            priority=int(data.get("priority", 3)),
            estimated_minutes=int(data.get("estimated_minutes", 30)),
            actual_minutes=int(data.get("actual_minutes", 0)),
            x=float(data.get("x", 100.0)),
            y=float(data.get("y", 100.0)),
            parent_id=data.get("parent_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            completed_at=data.get("completed_at"),
            tags=list(data.get("tags", [])),
            attachments=list(data.get("attachments", [])),
            repeat_type=_coerce_enum(
                RepeatType,
                data.get("repeat_type", legacy_routine.get("recurrence")),
                RepeatType.NONE,
            ),
            repeat_days=list(data.get("repeat_days", [])),
            repeat_interval=int(
                data.get(
                    "repeat_interval",
                    legacy_routine.get(
                        "interval_days",
                        legacy_routine.get("interval", 1),
                    ),
                )
            ),
            last_completed_at=data.get(
                "last_completed_at", legacy_routine.get("last_completed_at")
            ),
            next_due_at=data.get("next_due_at", legacy_routine.get("next_due_at")),
            streak=int(data.get("streak", legacy_routine.get("streak", 0))),
            resource_type=_coerce_enum(
                ResourceType, data.get("resource_type"), ResourceType.URL
            ),
            resource_path=data.get("resource_path", ""),
            checklist=[
                ChecklistItem.from_dict(item) for item in data.get("checklist", [])
            ],
            unlock_condition=data.get("unlock_condition", ""),
            duration_minutes=int(data.get("duration_minutes", 0)),
            locked=bool(data.get("locked", False)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class Edge:
    id: str
    source: str
    target: str
    type: EdgeType = EdgeType.DEPENDENCY
    label: str = ""
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type.value,
            "label": self.label,
            "weight": self.weight,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        return cls(
            id=data["id"],
            source=data["source"],
            target=data["target"],
            type=_coerce_enum(EdgeType, data.get("type"), EdgeType.DEPENDENCY),
            label=data.get("label", ""),
            weight=float(data.get("weight", 1.0)),
            metadata=dict(data.get("metadata", {})),
        )
