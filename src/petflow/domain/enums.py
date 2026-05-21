from __future__ import annotations

from enum import Enum


class NodeType(str, Enum):
    TASK = "task"
    ROUTINE = "routine"
    RESOURCE = "resource"
    CHECKPOINT = "checkpoint"
    REWARD = "reward"


class NodeStatus(str, Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    BLOCKED = "blocked"
    PAUSED = "paused"


class EdgeType(str, Enum):
    DEPENDENCY = "dependency"
    ROUTINE = "routine"
    RECOMMENDATION = "recommendation"
    TRIGGER = "trigger"


class RepeatType(str, Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ResourceType(str, Enum):
    URL = "url"
    FILE = "file"
    TEXT = "text"
    IMAGE = "image"
    CODE = "code"


class PetStateType(str, Enum):
    IDLE = "idle"
    MOVE = "move"
    HAPPY = "happy"
    ANGRY = "angry"
    THINK = "think"
    SLEEP = "sleep"


class EventType(str, Enum):
    GRAPH_CHANGED = "graph.changed"
    PROJECT_LOADED = "project.loaded"
    PROJECT_SAVED = "project.saved"
    NODE_ADDED = "graph.node_added"
    NODE_UPDATED = "graph.node_updated"
    NODE_REMOVED = "graph.node_removed"
    EDGE_ADDED = "graph.edge_added"
    EDGE_UPDATED = "graph.edge_updated"
    EDGE_REMOVED = "graph.edge_removed"
    PET_MOVED = "pet.moved"
    RECOMMENDATION_READY = "recommendation.ready"
    AGENT_PROPOSAL_READY = "agent.proposal_ready"
    CLIPBOARD_CAPTURED = "system.clipboard_captured"
    FOCUS_CHANGED = "system.focus_changed"

