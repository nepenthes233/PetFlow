from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from petflow.app.app_context import AppContext
from petflow.domain.entities import Edge, Node
from petflow.domain.enums import EdgeType, NodeStatus, NodeType
from petflow.domain.exceptions import PetFlowError
from petflow.ui.dialogs import EdgeDialog, NodeDialog
from petflow.ui.pet_view import PetView


class GraphCanvas(tk.Canvas):
    NODE_WIDTH = 172
    NODE_HEIGHT = 76

    def __init__(
        self,
        master: tk.Misc,
        context: AppContext,
        font_family: str = "TkDefaultFont",
        **kwargs,
    ) -> None:
        super().__init__(master, bg="#f5f7fb", highlightthickness=0, **kwargs)
        self.context = context
        self.font_family = font_family
        self._node_items: dict[str, list[int]] = {}
        self._item_to_node: dict[int, str] = {}
        self._edge_items: dict[str, list[int]] = {}
        self._item_to_edge: dict[int, str] = {}
        self._selected_node_id: str | None = None
        self._selected_edge_id: str | None = None
        self._drag_node_id: str | None = None
        self._drag_offset_x = 0.0
        self._drag_offset_y = 0.0
        self._pan_start_x = 0.0
        self._pan_start_y = 0.0
        self._pan_origin_x = 0.0
        self._pan_origin_y = 0.0
        self._panning = False
        self._edge_mode = False
        self._edge_start_node_id: str | None = None
        self._pet_view = PetView(self, self._to_screen)

        self.bind("<Button-1>", self._on_click)
        self.bind("<Shift-Button-1>", self._on_pan_start)
        self.bind("<Shift-B1-Motion>", self._on_pan_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        self.bind("<Button-4>", self._on_mouse_wheel)
        self.bind("<Button-5>", self._on_mouse_wheel)
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
        self._panning = False
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

    def mark_selected_node_status(self, status: NodeStatus) -> None:
        if self._selected_node_id is not None:
            self._mark_node_status(self._selected_node_id, status)

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

    def zoom_in(self) -> None:
        self._set_zoom(self.context.graph.workspace.zoom * 1.15)

    def zoom_out(self) -> None:
        self._set_zoom(self.context.graph.workspace.zoom / 1.15)

    def reset_view(self) -> None:
        workspace = self.context.graph.workspace
        workspace.zoom = 1.0
        workspace.pan_x = 0.0
        workspace.pan_y = 0.0
        self.redraw()

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
        self._pet_view.draw(self.context.graph.pet)

    def _draw_empty_hint(self) -> None:
        x, y = self._to_screen(80, 40)
        self.create_text(
            x,
            y,
            text="PetFlow task graph",
            anchor="w",
            fill="#334155",
            font=(self.font_family, 16, "bold"),
        )
        x, y = self._to_screen(80, 72)
        self.create_text(
            x,
            y,
            text="Click New Node to start building your workflow.",
            anchor="w",
            fill="#64748b",
            font=(self.font_family, 11),
        )

    def _draw_node(self, node: Node) -> None:
        x1, y1 = self._to_screen(node.x, node.y)
        x2, y2 = self._to_screen(node.x + self.NODE_WIDTH, node.y + self.NODE_HEIGHT)
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
            x1 + self._scale(12),
            y1 + self._scale(14),
            text=node.type.value.upper(),
            anchor="w",
            fill="#475569",
            font=(self.font_family, 9, "bold"),
            tags=("node", f"node:{node.id}"),
        )
        title = self.create_text(
            x1 + self._scale(12),
            y1 + self._scale(38),
            text=self._fit_text(node.title, 22),
            anchor="w",
            fill="#0f172a",
            font=(self.font_family, 12, "bold"),
            tags=("node", f"node:{node.id}"),
        )
        meta = self.create_text(
            x1 + self._scale(12),
            y1 + self._scale(60),
            text=self._node_meta_text(node),
            anchor="w",
            fill="#475569",
            font=(self.font_family, 9),
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

        start_x, start_y = self._to_screen(
            source.x + self.NODE_WIDTH,
            source.y + self.NODE_HEIGHT / 2,
        )
        end_x, end_y = self._to_screen(target.x, target.y + self.NODE_HEIGHT / 2)
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
            text=self._edge_label_text(edge),
            fill=color,
            font=(self.font_family, 8),
            tags=("edge", f"edge:{edge.id}"),
        )
        items = [line, label]
        self._edge_items[edge.id] = items
        for item in items:
            self._item_to_edge[item] = edge.id

    def _on_click(self, event: tk.Event) -> None:
        if event.state & 0x0001:
            return
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
                graph_x, graph_y = self._event_graph_position(event)
                self._drag_node_id = node_id
                self._drag_offset_x = graph_x - node.x
                self._drag_offset_y = graph_y - node.y

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag_node_id is None:
            return
        graph_x, graph_y = self._event_graph_position(event)
        x = graph_x - self._drag_offset_x
        y = graph_y - self._drag_offset_y
        self.context.graph_service.move_node(
            self._drag_node_id, max(0.0, x), max(0.0, y)
        )
        self.redraw()

    def _on_release(self, _event: tk.Event) -> None:
        self._drag_node_id = None
        self._panning = False

    def _on_pan_start(self, event: tk.Event) -> None:
        self._panning = True
        self._drag_node_id = None
        self._pan_start_x = float(event.x)
        self._pan_start_y = float(event.y)
        self._pan_origin_x = self.context.graph.workspace.pan_x
        self._pan_origin_y = self.context.graph.workspace.pan_y

    def _on_pan_drag(self, event: tk.Event) -> None:
        if not self._panning:
            return
        workspace = self.context.graph.workspace
        workspace.pan_x = self._pan_origin_x + float(event.x) - self._pan_start_x
        workspace.pan_y = self._pan_origin_y + float(event.y) - self._pan_start_y
        self.redraw()

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        if getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            self.zoom_out()
        else:
            self.zoom_in()

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
        menu.add_separator()
        menu.add_command(
            label="Mark Todo",
            command=lambda: self._mark_node_status(node_id, NodeStatus.TODO),
        )
        menu.add_command(
            label="Mark Doing",
            command=lambda: self._mark_node_status(node_id, NodeStatus.DOING),
        )
        menu.add_command(
            label="Mark Done",
            command=lambda: self._mark_node_status(node_id, NodeStatus.DONE),
        )
        menu.add_command(
            label="Mark Blocked",
            command=lambda: self._mark_node_status(node_id, NodeStatus.BLOCKED),
        )
        menu.add_command(
            label="Mark Paused",
            command=lambda: self._mark_node_status(node_id, NodeStatus.PAUSED),
        )
        menu.add_separator()
        menu.add_command(
            label="Delete Node", command=lambda: self._delete_node(node_id)
        )
        menu.add_separator()
        menu.add_command(
            label="Agent Split",
            command=lambda: self._open_agent_split(node_id),
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
                actual_minutes=int(dialog.result["actual_minutes"]),
                tags=dialog.result["tags"],
                resource_type=dialog.result["resource_type"],
                resource_path=str(dialog.result["resource_path"]),
                checklist=dialog.result["checklist"],
                repeat_type=dialog.result["repeat_type"],
                next_due_at=str(dialog.result["next_due_at"]),
                streak=int(dialog.result["streak"]),
            )
            self.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Edit node failed", str(exc), parent=self)

    def _mark_node_status(self, node_id: str, status: NodeStatus) -> None:
        try:
            self.context.graph_service.update_node_status(node_id, status)
            self._selected_node_id = node_id
            self.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Update status failed", str(exc), parent=self)

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
        if item:
            edge_id = self._item_to_edge.get(item[0])
            if edge_id is not None:
                return edge_id
        radius = 6
        for item_id in self.find_overlapping(
            event.x - radius,
            event.y - radius,
            event.x + radius,
            event.y + radius,
        ):
            edge_id = self._item_to_edge.get(item_id)
            if edge_id is not None:
                return edge_id
        return None

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
                label=str(dialog.result["label"]),
            )
            self._selected_edge_id = None
            self.cancel_edge_mode()
            self.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Create edge failed", str(exc), parent=self)

    def _open_agent_split(self, node_id: str) -> None:
        main_window = self.master
        while main_window is not None and not hasattr(main_window, "open_agent_dialog"):
            main_window = getattr(main_window, "master", None)
        if main_window is None:
            messagebox.showerror("Agent", "Agent dialog is unavailable.", parent=self)
            return
        main_window.open_agent_dialog(node_id=node_id)

    def _set_zoom(self, zoom: float) -> None:
        self.context.graph.workspace.zoom = min(2.5, max(0.4, zoom))
        self.redraw()

    def _event_graph_position(self, event: tk.Event) -> tuple[float, float]:
        return self._to_graph(float(event.x), float(event.y))

    def _to_screen(self, x: float, y: float) -> tuple[float, float]:
        workspace = self.context.graph.workspace
        return (
            x * workspace.zoom + workspace.pan_x,
            y * workspace.zoom + workspace.pan_y,
        )

    def _to_graph(self, x: float, y: float) -> tuple[float, float]:
        workspace = self.context.graph.workspace
        zoom = workspace.zoom or 1.0
        return (
            (x - workspace.pan_x) / zoom,
            (y - workspace.pan_y) / zoom,
        )

    def _scale(self, value: float) -> float:
        return value * self.context.graph.workspace.zoom

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

    @classmethod
    def _edge_label_text(cls, edge: Edge) -> str:
        if edge.label:
            return cls._fit_text(edge.label, 28)
        return edge.type.value

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

    def _node_meta_text(self, node: Node) -> str:
        parts = [node.status.value, f"P{node.priority}", f"{node.estimated_minutes}m"]
        if node.type == NodeType.ROUTINE:
            state = self._routine_state_label(node)
            if state:
                parts.append(state)
        return " | ".join(parts)

    def _routine_state_label(self, node: Node) -> str:
        state = self.context.routine_service.routine_state(node)
        if state == "overdue":
            return "overdue"
        if state == "due":
            return "due"
        if state == "scheduled":
            return "scheduled"
        return ""
