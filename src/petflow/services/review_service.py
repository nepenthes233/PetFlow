from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from petflow.domain.enums import NodeStatus, NodeType
from petflow.domain.graph import GraphModel


@dataclass(slots=True)
class ReviewService:
    def summary_text(self, graph: GraphModel) -> str:
        completed_nodes = [
            node for node in graph.nodes.values() if node.status == NodeStatus.DONE
        ]
        active_nodes = [
            node
            for node in graph.nodes.values()
            if node.status in {NodeStatus.TODO, NodeStatus.DOING, NodeStatus.PAUSED}
        ]
        blocked_nodes = [
            node for node in graph.nodes.values() if node.status == NodeStatus.BLOCKED
        ]
        routine_nodes = [
            node for node in graph.nodes.values() if node.type == NodeType.ROUTINE
        ]
        completed_titles = ", ".join(node.title for node in completed_nodes[:5]) or "-"
        active_titles = ", ".join(node.title for node in active_nodes[:5]) or "-"
        return "\n".join(
            [
                "PetFlow Review",
                f"Completed: {len(completed_nodes)}",
                f"Active: {len(active_nodes)}",
                f"Blocked: {len(blocked_nodes)}",
                f"Routines: {len(routine_nodes)}",
                f"Recent completed: {completed_titles}",
                f"Next candidates: {active_titles}",
                f"History entries: {len(graph.history)}",
            ]
        )

    def format_agent_review(
        self,
        response: dict[str, Any],
        fallback: str,
    ) -> str:
        summary = str(response.get("summary", "")).strip()
        highlights = response.get("highlights", [])
        if not summary:
            return fallback
        lines = ["PetFlow Review", summary]
        if isinstance(highlights, list) and highlights:
            lines.append("")
            lines.append("Highlights:")
            for item in highlights[:5]:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")
        return "\n".join(lines)
