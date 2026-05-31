from __future__ import annotations

from petflow.domain.entities import Node
from petflow.domain.enums import EdgeType
from petflow.domain.graph import GraphModel


class PromptBuilder:
    _PROPOSAL_SCHEMA = (
        "Return only a JSON object with `nodes` and `edges` arrays. "
        "Each node may use: id, type, title, description, status, priority, "
        "estimated_minutes, actual_minutes, tags, checklist, resource_type, "
        "resource_path, repeat_type, repeat_interval, next_due_at, x, y. "
        "For deadlines or due dates, set next_due_at as YYYY-MM-DD or ISO datetime; "
        "deadline, due_date, and due_at are accepted aliases. "
        "For routines, set type to routine when appropriate and use repeat_type "
        "(none, daily, weekly, monthly), repeat_interval, next_due_at, and streak. "
        "A nested routine object with recurrence, interval_days, next_due_at, and "
        "streak is also accepted. "
        "Allowed node types: task, routine, resource, checkpoint, reward. "
        "Use status values only from: todo, doing, done, blocked, paused. "
        "Use priority as an integer from 1 to 5, not words such as high or low. "
        "Each edge may use: source, target, type, label. "
        "Allowed edge types: dependency, routine, recommendation, trigger. "
        "Every edge source and target must refer to an id in the returned nodes array. "
        "To update existing nodes, include update_nodes with id or query plus fields "
        "to change, such as title, status, deadline/due_date, routine, repeat_type, "
        "repeat_interval, priority, estimated_minutes, actual_minutes, tags, or "
        "checklist. To add edges between existing or new nodes, include add_edges "
        "with source/target ids or source_query/target_query. "
        "To delete existing nodes, include delete_node_ids as an array of exact ids "
        "from the existing context. If the user asks to delete everything or clear "
        "the canvas, set delete_all_nodes to true. If the user describes what to "
        "delete but does not name an exact id, set delete_query to the target phrase; "
        "PetFlow will match it against node titles, descriptions, types, status, "
        "and tags. To arrange the graph, include "
        '`layout`: {"enabled": true, "strategy": "flow"}. '
        'Example JSON shape: {"nodes": [{"id": "step_1", "type": "task", '
        '"title": "Start"}], "edges": [], "delete_node_ids": [], '
        '"delete_all_nodes": false, "delete_query": "", '
        '"layout": {"enabled": false}}. '
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
            "If the user explicitly asks to delete/remove a task, return its exact "
            "id in delete_node_ids. If the user asks to delete all nodes, clear the "
            "graph, or empty the canvas, return delete_all_nodes true. "
            "If the delete request is fuzzy, return delete_query with the shortest "
            "matching phrase, such as a title keyword or tag. "
            "If the user asks to rename, mark done, change status, deadline, routine, "
            "or other fields on existing tasks, use update_nodes. If the user asks "
            "to connect/link/make one task depend on another, use add_edges. "
            "If the user asks to organize, arrange, clean up, "
            "or re-layout the canvas, return layout.enabled true. "
            "Use resource nodes only for useful inputs and reward nodes sparingly. "
            "Use optional scheduling fields when the user specifies dates or "
            "recurrence. "
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
            lines.append(
                f"- {node.id}: {node.title} [{node.type.value}, {node.status.value}]"
            )
        return "\n".join(lines)
