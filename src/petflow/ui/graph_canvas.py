from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from petflow.app.app_context import AppContext
from petflow.domain.entities import Edge, Node
from petflow.domain.enums import EdgeType, NodeStatus, NodeType
from petflow.domain.exceptions import PetFlowError
from petflow.ui.dialogs import EdgeDialog, NodeDialog


class GraphCanvas(tk.Canvas):
    NODE_WIDTH = 172
    NODE_HEIGHT = 76

    def __init__(self, master: tk.Misc, context: AppContext, **kwargs) -> None:
        super().__init__(master, bg="#f5f7fb", highlightthickness=0, **kwargs)
        self.context = context
        self._node_items: dict[str, list[int]] = {}
        self._item_to_node: dict[int, str] = {}
        self._edge_items: dict[str, list[int]] = {}
        self._item_to_edge: dict[int, str] = {}
        self._selected_node_id: str | None = None
        self._selected_edge_id: str | None = None
        self._drag_node_id: str | None = None
        self._drag_offset_x = 0.0
        self._drag_offset_y = 0.0
        self._edge_mode = False
        self._edge_start_node_id: str | None = None

        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Button-2>", self._on_context_menu)
        self.bind("<Button-3>", self._on_context_menu)
        self.bind("<Delete>", self._on_delete_key)
        self.bind("<BackSpace>", self._on_delete_key)
        self.redraw()

    def set_context(self, context: AppContext) -> None:
        self.context = context
        self._selected_node_id = None
        self._selected_edge_id = None
        self._edge_mode = False
        self._edge_start_node_id = None
        self.redraw()

    def redraw(self) -> None:
        self._redraw()

    def selected_node_id(self) -> str | None:
        return self._selected_node_id

    def selected_edge_id(self) -> str | None:
        return self._selected_edge_id

    def select_node(self, node_id: str | None) -> None:
        if node_id is not None and self.context.graph.get_node(node_id) is None:
            node_id = None
        self._selected_node_id = node_id
        self.context.graph_service.set_current_node(node_id)
        self.focus_set()
        self.redraw()

    def edit_selected_node(self) -> None:
        if self._selected_node_id is not None:
            self._edit_node(self._selected_node_id)

    def delete_selected_node(self) -> None:
        if self._selected_node_id is not None:
            self._delete_node(self._selected_node_id)

    def begin_edge_mode(self) -> None:
        self._edge_mode = True
        self._edge_start_node_id = None
        self._selected_edge_id = None
        self.redraw()

    def cancel_edge_mode(self) -> None:
        self._edge_mode = False
        self._edge_start_node_id = None
        self.redraw()

    def delete_selected_edge(self) -> None:
        if self._selected_edge_id is not None:
            self._delete_edge(self._selected_edge_id)

    def edit_selected_edge(self) -> None:
        if self._selected_edge_id is not None:
            self._edit_edge(self._selected_edge_id)

    def _redraw(self) -> None:
        self.delete("all")
        self._node_items.clear()
        self._item_to_node.clear()
        self._edge_items.clear()
        self._item_to_edge.clear()

        if not self.context.graph.nodes:
            self._draw_empty_hint()
            return

        for edge in self.context.graph.edges.values():
            self._draw_edge(edge)
        for node in self.context.graph.nodes.values():
            self._draw_node(node)

    def _draw_empty_hint(self) -> None:
        self.create_text(
            80,
            40,
            text="PetFlow task graph",
            anchor="w",
            fill="#334155",
            font=("Arial", 16, "bold"),
        )
        self.create_text(
            80,
            72,
            text="Click New Node to start building your workflow.",
            anchor="w",
            fill="#64748b",
            font=("Arial", 11),
        )

    def _draw_node(self, node: Node) -> None:
        x1 = node.x
        y1 = node.y
        x2 = x1 + self.NODE_WIDTH
        y2 = y1 + self.NODE_HEIGHT
        fill = self._node_fill(node)
        outline = "#0f172a" if node.id == self._selected_node_id else "#94a3b8"
        width = 2 if node.id == self._selected_node_id else 1

        rect = self.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=fill,
            outline=outline,
            width=width,
            tags=("node", f"node:{node.id}"),
        )
        type_text = self.create_text(
            x1 + 12,
            y1 + 14,
            text=node.type.value.upper(),
            anchor="w",
            fill="#475569",
            font=("Arial", 9, "bold"),
            tags=("node", f"node:{node.id}"),
        )
        title = self.create_text(
            x1 + 12,
            y1 + 38,
            text=self._fit_text(node.title, 22),
            anchor="w",
            fill="#0f172a",
            font=("Arial", 12, "bold"),
            tags=("node", f"node:{node.id}"),
        )
        meta = self.create_text(
            x1 + 12,
            y1 + 60,
            text=f"{node.status.value} | P{node.priority} | {node.estimated_minutes}m",
            anchor="w",
            fill="#475569",
            font=("Arial", 9),
            tags=("node", f"node:{node.id}"),
        )
        items = [rect, type_text, title, meta]
        self._node_items[node.id] = items
        for item in items:
            self._item_to_node[item] = node.id

    def _draw_edge(self, edge: Edge) -> None:
        source = self.context.graph.get_node(edge.source)
        target = self.context.graph.get_node(edge.target)
        if source is None or target is None:
            return

        start_x = source.x + self.NODE_WIDTH
        start_y = source.y + self.NODE_HEIGHT / 2
        end_x = target.x
        end_y = target.y + self.NODE_HEIGHT / 2
        color, dash = self._edge_style(edge)
        width = 3 if edge.id == self._selected_edge_id else 2

        line = self.create_line(
            start_x,
            start_y,
            end_x,
            end_y,
            fill=color,
            width=width,
            arrow=tk.LAST,
            smooth=True,
            splinesteps=20,
            dash=dash,
            tags=("edge", f"edge:{edge.id}"),
        )
        label = self.create_text(
            (start_x + end_x) / 2,
            (start_y + end_y) / 2 - 12,
            text=edge.type.value,
            fill=color,
            font=("Arial", 8),
            tags=("edge", f"edge:{edge.id}"),
        )
        items = [line, label]
        self._edge_items[edge.id] = items
        for item in items:
            self._item_to_edge[item] = edge.id

    def _on_click(self, event: tk.Event) -> None:
        node_id = self._node_id_from_event(event)
        edge_id = self._edge_id_from_event(event)
        self._drag_node_id = None
        if self._edge_mode and node_id is not None:
            self._handle_edge_mode_click(node_id)
            return
        self._selected_edge_id = edge_id
        self.select_node(node_id)
        if node_id is not None:
            node = self.context.graph.get_node(node_id)
            if node is not None:
                self._drag_node_id = node_id
                self._drag_offset_x = float(event.x) - node.x
                self._drag_offset_y = float(event.y) - node.y

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag_node_id is None:
            return
        x = float(event.x) - self._drag_offset_x
        y = float(event.y) - self._drag_offset_y
        self.context.graph_service.move_node(
            self._drag_node_id, max(0.0, x), max(0.0, y)
        )
        self.redraw()

    def _on_release(self, _event: tk.Event) -> None:
        self._drag_node_id = None

    def _on_double_click(self, event: tk.Event) -> None:
        node_id = self._node_id_from_event(event)
        if node_id is None:
            return
        self._edit_node(node_id)

    def _on_context_menu(self, event: tk.Event) -> None:
        node_id = self._node_id_from_event(event)
        edge_id = self._edge_id_from_event(event)
        if edge_id is not None:
            self._selected_edge_id = edge_id
            self._selected_node_id = None
            self.context.graph_service.set_current_node(None)
            self.redraw()
            menu = tk.Menu(self, tearoff=False)
            menu.add_command(
                label="Edit Edge", command=lambda: self._edit_edge(edge_id)
            )
            menu.add_command(
                label="Delete Edge", command=lambda: self._delete_edge(edge_id)
            )
            menu.add_command(label="Cancel Edge Mode", command=self.cancel_edge_mode)
            menu.tk_popup(event.x_root, event.y_root)
            return
        if node_id is None:
            return
        self.select_node(node_id)
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Edit Node", command=lambda: self._edit_node(node_id))
        menu.add_command(
            label="Delete Node", command=lambda: self._delete_node(node_id)
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _on_delete_key(self, _event: tk.Event) -> None:
        if self._selected_edge_id is not None:
            self._delete_edge(self._selected_edge_id)
            return
        self.delete_selected_node()

    def _edit_node(self, node_id: str) -> None:
        node = self.context.graph.get_node(node_id)
        if node is None:
            return
        dialog = NodeDialog(self, node)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.context.graph_service.update_node_detail(
                node_id,
                title=str(dialog.result["title"]),
                description=str(dialog.result["description"]),
                node_type=dialog.result["node_type"],
                status=dialog.result["status"],
                priority=int(dialog.result["priority"]),
                estimated_minutes=int(dialog.result["estimated_minutes"]),
            )
            self.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Edit node failed", str(exc), parent=self)

    def _delete_node(self, node_id: str) -> None:
        if not messagebox.askyesno("Delete node", "Delete this node?", parent=self):
            return
        try:
            self.context.graph_service.delete_node(node_id)
            self._selected_node_id = None
            self.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Delete node failed", str(exc), parent=self)

    def _delete_edge(self, edge_id: str) -> None:
        if not messagebox.askyesno("Delete edge", "Delete this edge?", parent=self):
            return
        try:
            self.context.graph_service.delete_edge(edge_id)
            self._selected_edge_id = None
            self.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Delete edge failed", str(exc), parent=self)

    def _edit_edge(self, edge_id: str) -> None:
        edge = self.context.graph.get_edge(edge_id)
        if edge is None:
            return
        dialog = EdgeDialog(self, edge)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.context.graph_service.update_edge(
                edge_id,
                type=dialog.result["type"],
                label=str(dialog.result["label"]),
            )
            self.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Edit edge failed", str(exc), parent=self)

    def _node_id_from_event(self, event: tk.Event) -> str | None:
        item = self.find_withtag("current")
        if not item:
            return None
        return self._item_to_node.get(item[0])

    def _edge_id_from_event(self, event: tk.Event) -> str | None:
        item = self.find_withtag("current")
        if not item:
            return None
        return self._item_to_edge.get(item[0])

    def _handle_edge_mode_click(self, node_id: str) -> None:
        if self._edge_start_node_id is None:
            self._edge_start_node_id = node_id
            self._selected_node_id = node_id
            self.redraw()
            return
        if self._edge_start_node_id == node_id:
            return
        dialog = EdgeDialog(self)
        self.wait_window(dialog)
        if dialog.result is None:
            self.cancel_edge_mode()
            return
        try:
            self.context.graph_service.create_edge(
                self._edge_start_node_id,
                node_id,
                dialog.result["type"],
            )
            self._selected_edge_id = None
            self.cancel_edge_mode()
            self.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Create edge failed", str(exc), parent=self)

    @staticmethod
    def _edge_style(edge: Edge) -> tuple[str, tuple[int, ...] | None]:
        if edge.type == EdgeType.DEPENDENCY:
            return "#1d4ed8", None
        if edge.type == EdgeType.ROUTINE:
            return "#059669", (6, 4)
        if edge.type == EdgeType.RECOMMENDATION:
            return "#7c3aed", (2, 4)
        if edge.type == EdgeType.TRIGGER:
            return "#ea580c", None
        return "#475569", None

    @staticmethod
    def _fit_text(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "..."

    @staticmethod
    def _node_fill(node: Node) -> str:
        if node.type == NodeType.RESOURCE:
            return "#ccfbf1"
        if node.type == NodeType.REWARD:
            return "#fce7f3"
        if node.type == NodeType.CHECKPOINT:
            return "#e0e7ff"
        if node.status == NodeStatus.DOING:
            return "#fef3c7"
        if node.status == NodeStatus.DONE:
            return "#dcfce7"
        if node.status == NodeStatus.BLOCKED:
            return "#fee2e2"
        if node.status == NodeStatus.PAUSED:
            return "#ede9fe"
        return "#dbeafe"
