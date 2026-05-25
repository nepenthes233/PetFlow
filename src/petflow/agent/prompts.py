from __future__ import annotations

from petflow.domain.entities import Node
from petflow.domain.enums import EdgeType
from petflow.domain.graph import GraphModel


class PromptBuilder:
    _PROPOSAL_SCHEMA = (
        "Return only a JSON object with `nodes` and `edges` arrays. "
        "Each node may use: id, type, title, description, status, priority, "
        "estimated_minutes, repeat_type, repeat_interval, next_due_at, x, y. "
        "Allowed node types: task, routine, resource, checkpoint, reward. "
        "Use status values only from: todo, doing, done, blocked, paused. "
        "Use priority as an integer from 1 to 5, not words such as high or low. "
        "Each edge may use: source, target, type, label. "
        "Allowed edge types: dependency, routine, recommendation, trigger. "
        "Every edge source and target must refer to an id in the returned nodes array. "
        'Example JSON shape: {"nodes": [{"id": "step_1", "type": "task", '
        '"title": "Start"}], "edges": []}. '
    )

    def build_graph_generation_prompt(self, user_goal: str) -> str:
        return (
            "Create a practical PetFlow task graph for the user's goal. "
            "Use 3 to 10 nodes, arranged as a clear left-to-right workflow. "
            f"{self._PROPOSAL_SCHEMA}\n"
            f"User goal: {user_goal}"
        )

    def build_companion_planning_prompt(
        self, user_message: str, graph: GraphModel
    ) -> str:
        existing = self._existing_graph_summary(graph)
        return (
            "You are the planning companion inside PetFlow. "
            "Turn the user's message into a concise actionable workflow that can be "
            "added to the canvas. Avoid duplicating existing tasks when possible. "
            "Use resource nodes only for useful inputs and reward nodes sparingly. "
            "Use optional scheduling fields when the user specifies dates or recurrence. "
            f"{self._PROPOSAL_SCHEMA}\n"
            f"Existing canvas context:\n{existing}\n"
            f"User message: {user_message}"
        )

    def build_companion_chat_prompt(
        self, user_message: str, graph: GraphModel
    ) -> str:
        existing = self._existing_graph_summary(graph)
        return (
            "You are the helpful desktop companion inside PetFlow. "
            "Answer the user's question concisely and practically. "
            "Do not generate or modify task nodes in this mode. "
            "Return only a JSON object with a single `reply` string field.\n"
            f"Current task context:\n{existing}\n"
            f"User message: {user_message}"
        )

    def build_node_split_prompt(self, graph: GraphModel, node: Node) -> str:
        predecessors = graph.predecessors(node.id, [EdgeType.DEPENDENCY])
        successors = graph.successors(node.id, [EdgeType.DEPENDENCY])
        predecessor_titles = ", ".join(item.title for item in predecessors) or "none"
        successor_titles = ", ".join(item.title for item in successors) or "none"
        tags = ", ".join(node.tags) or "none"
        return (
            "Split the selected PetFlow node into 3 to 6 executable subtasks. "
            "Keep estimates realistic and do not duplicate existing nodes. "
            f"{self._PROPOSAL_SCHEMA}\n"
            f"Selected node: {node.title}\n"
            f"Description: {node.description or 'none'}\n"
            f"Predecessors: {predecessor_titles}\n"
            f"Successors: {successor_titles}\n"
            f"Estimated minutes: {node.estimated_minutes}\n"
            f"Tags: {tags}\n"
            f"Existing node count: {len(graph.nodes)}"
        )

    def build_review_prompt(self, summary: str) -> str:
        return (
            "Generate a short review of task progress. Return only a JSON object "
            "with `summary` as a string and `highlights` as an array of strings.\n"
            f"Progress summary: {summary}"
        )

    @staticmethod
    def _existing_graph_summary(graph: GraphModel) -> str:
        if not graph.nodes:
            return "- empty canvas"
        lines = []
        for node in list(graph.nodes.values())[:12]:
            lines.append(f"- {node.title} [{node.type.value}, {node.status.value}]")
        return "\n".join(lines)
