from __future__ import annotations

import re
from typing import Any

from petflow.app.graph_service import GraphService
from petflow.agent.proposal import AgentProposalValidator
from petflow.domain.entities import Node
from petflow.domain.enums import EdgeType, NodeStatus, NodeType, RepeatType
from petflow.domain.exceptions import GraphValidationError
from petflow.services.graph_layout_service import GraphLayoutService


class AgentExecutor:
    def __init__(
        self,
        graph_service: GraphService,
        validator: AgentProposalValidator | None = None,
        layout_service: GraphLayoutService | None = None,
    ) -> None:
        self.graph_service = graph_service
        self.validator = validator or AgentProposalValidator()
        self.layout_service = layout_service or GraphLayoutService()
        self.last_deleted_node_ids: list[str] = []
        self.last_updated_node_ids: list[str] = []
        self.last_added_edge_ids: list[str] = []
        self.last_layout_requested = False

    def apply_graph_proposal(
        self,
        proposal: dict[str, Any],
        parent_node_id: str | None = None,
    ) -> list[Node]:
        proposal = self.validator.validate(proposal)
        self.last_deleted_node_ids = []
        self.last_updated_node_ids = []
        self.last_added_edge_ids = []
        layout = proposal.get("layout", {})
        self.last_layout_requested = (
            isinstance(layout, dict) and bool(layout.get("enabled", False))
        )
        if (
            parent_node_id is not None
            and self.graph_service.graph.get_node(parent_node_id) is None
        ):
            raise GraphValidationError(f"Missing parent node: {parent_node_id}")
        delete_all_nodes = bool(proposal.get("delete_all_nodes", False))
        if parent_node_id is not None and delete_all_nodes:
            raise GraphValidationError("Agent split cannot delete all nodes.")
        delete_node_ids = list(proposal.get("delete_node_ids", []))
        if delete_all_nodes:
            delete_node_ids = list(self.graph_service.graph.nodes)
        delete_query = str(proposal.get("delete_query", "")).strip()
        if delete_query:
            delete_node_ids.extend(self._resolve_delete_query(delete_query))
        delete_node_ids = list(
            dict.fromkeys(str(node_id) for node_id in delete_node_ids)
        )
        if parent_node_id is not None and parent_node_id in delete_node_ids:
            raise GraphValidationError("Agent split cannot delete the parent node.")
        for node_id in delete_node_ids:
            if self.graph_service.graph.get_node(str(node_id)) is None:
                raise GraphValidationError(f"Missing node to delete: {node_id}")
            self.graph_service.delete_node(str(node_id))
            self.last_deleted_node_ids.append(str(node_id))
        id_map: dict[str, str] = {}
        created_nodes: list[Node] = []
        for node_data in proposal.get("nodes", []):
            node = self.graph_service.create_node(
                title=str(node_data["title"]),
                description=str(node_data.get("description", "")),
                node_type=NodeType(node_data.get("type", NodeType.TASK.value)),
                status=NodeStatus(node_data.get("status", NodeStatus.TODO.value)),
                priority=int(node_data.get("priority", 3)),
                estimated_minutes=int(node_data.get("estimated_minutes", 30)),
                actual_minutes=int(node_data.get("actual_minutes", 0)),
                tags=list(node_data.get("tags", [])),
                resource_type=node_data.get("resource_type", "url"),
                resource_path=str(node_data.get("resource_path", "")),
                checklist=list(node_data.get("checklist", [])),
                repeat_type=RepeatType(
                    node_data.get("repeat_type", RepeatType.NONE.value)
                ),
                repeat_interval=int(node_data.get("repeat_interval", 1)),
                next_due_at=node_data.get("next_due_at"),
                streak=int(node_data.get("streak", 0)),
                x=float(node_data.get("x", 100.0)),
                y=float(node_data.get("y", 100.0)),
            )
            id_map[node_data.get("id", node.id)] = node.id
            created_nodes.append(node)

        for edge_data in proposal.get("edges", []):
            source = id_map.get(edge_data.get("source"), edge_data.get("source"))
            target = id_map.get(edge_data.get("target"), edge_data.get("target"))
            if source and target:
                edge = self.graph_service.create_edge(
                    source=source,
                    target=target,
                    edge_type=EdgeType(
                        edge_data.get("type", EdgeType.DEPENDENCY.value)
                    ),
                    label=edge_data.get("label", ""),
                )
                self.last_added_edge_ids.append(edge.id)
        for edge_data in proposal.get("add_edges", []):
            source = self._resolve_single_node_ref(
                str(edge_data.get("source", "")),
                str(edge_data.get("source_query", "")),
                id_map,
                role="source",
            )
            target = self._resolve_single_node_ref(
                str(edge_data.get("target", "")),
                str(edge_data.get("target_query", "")),
                id_map,
                role="target",
            )
            edge = self.graph_service.create_edge(
                source=source,
                target=target,
                edge_type=EdgeType(edge_data.get("type", EdgeType.DEPENDENCY.value)),
                label=edge_data.get("label", ""),
            )
            self.last_added_edge_ids.append(edge.id)
        for update in proposal.get("update_nodes", []):
            target_ids = self._resolve_node_refs(
                str(update.get("node_id", "")),
                str(update.get("query", "")),
                id_map,
            )
            for node_id in target_ids:
                self._apply_node_update(node_id, dict(update.get("changes", {})))
                self.last_updated_node_ids.append(node_id)
        if parent_node_id is not None:
            for node in created_nodes:
                edge = self.graph_service.create_edge(
                    parent_node_id,
                    node.id,
                    EdgeType.RECOMMENDATION,
                    label="agent split",
                )
                self.last_added_edge_ids.append(edge.id)
        if self.last_layout_requested:
            self.layout_service.apply_grid_layout(self.graph_service)
        return created_nodes

    def _resolve_delete_query(self, query: str) -> list[str]:
        matches = self._find_matching_node_ids(query)
        if not matches:
            raise GraphValidationError(f"No nodes match delete query: {query}")
        return matches

    def _resolve_node_refs(
        self,
        node_id: str,
        query: str,
        id_map: dict[str, str],
    ) -> list[str]:
        node_id = node_id.strip()
        if node_id:
            resolved = id_map.get(node_id, node_id)
            if self.graph_service.graph.get_node(resolved) is None:
                raise GraphValidationError(f"Missing node: {node_id}")
            return [resolved]
        query = query.strip()
        if not query:
            return []
        matches = self._find_matching_node_ids(query)
        if not matches:
            raise GraphValidationError(f"No nodes match query: {query}")
        return matches

    def _resolve_single_node_ref(
        self,
        node_id: str,
        query: str,
        id_map: dict[str, str],
        *,
        role: str,
    ) -> str:
        matches = self._resolve_node_refs(node_id, query, id_map)
        if not matches:
            raise GraphValidationError(f"Missing {role} node for edge.")
        if len(matches) > 1:
            raise GraphValidationError(
                f"Edge {role} query matched multiple nodes: {query}"
            )
        return matches[0]

    def _find_matching_node_ids(self, query: str) -> list[str]:
        normalized_query = self._normalize_search_text(query)
        tokens = [
            token
            for token in re.split(r"\s+", normalized_query)
            if token and token not in {"delete", "remove", "node", "task", "删除"}
        ]
        matches: list[str] = []
        for node in self.graph_service.graph.nodes.values():
            haystack = self._normalize_search_text(
                " ".join(
                    [
                        node.id,
                        node.title,
                        node.description,
                        node.type.value,
                        node.status.value,
                        " ".join(node.tags),
                    ]
                )
            )
            if normalized_query and normalized_query in haystack:
                matches.append(node.id)
            elif tokens and all(token in haystack for token in tokens):
                matches.append(node.id)
        return matches

    def _apply_node_update(self, node_id: str, changes: dict[str, Any]) -> None:
        if not changes:
            return
        node = self.graph_service.graph.get_node(node_id)
        if node is None:
            raise GraphValidationError(f"Missing node: {node_id}")
        self.graph_service.update_node_detail(
            node_id,
            title=str(changes.get("title", node.title)),
            description=str(changes.get("description", node.description)),
            node_type=changes.get("type", node.type),
            status=changes.get("status", node.status),
            priority=int(changes.get("priority", node.priority)),
            estimated_minutes=int(
                changes.get("estimated_minutes", node.estimated_minutes)
            ),
            actual_minutes=int(changes.get("actual_minutes", node.actual_minutes)),
            tags=changes.get("tags", node.tags),
            resource_type=changes.get("resource_type", node.resource_type),
            resource_path=str(changes.get("resource_path", node.resource_path)),
            checklist=changes.get("checklist", node.checklist),
            repeat_type=changes.get("repeat_type", node.repeat_type),
            repeat_interval=int(changes.get("repeat_interval", node.repeat_interval)),
            next_due_at=changes.get("next_due_at", node.next_due_at),
            streak=int(changes.get("streak", node.streak)),
        )

    @staticmethod
    def _normalize_search_text(value: str) -> str:
        return " ".join(str(value).casefold().split())
