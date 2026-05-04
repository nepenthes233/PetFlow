from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from petflow.app.app_context import AppContext
from petflow.config import DEFAULT_GRAPH_PATH, AppConfig
from petflow.domain.enums import NodeStatus
from petflow.domain.exceptions import PetFlowError
from petflow.system.clipboard_watcher import ClipboardWatcher
from petflow.ui.agent_dialog import AgentDialog
from petflow.ui.dialogs import NodeDialog
from petflow.ui.graph_canvas import GraphCanvas


class MainWindow:
    def __init__(self) -> None:
        self.config = AppConfig()
        self.context = AppContext.create()
        self.graph = self.context.storage_service.load_graph(DEFAULT_GRAPH_PATH)
        self.context = AppContext.create(self.graph)
        self.clipboard_watcher = ClipboardWatcher()
        self.focus_started_at: datetime | None = None
        self.status_message = "Ready"
        self.status_after_id: str | None = None

        self.root = tk.Tk()
        self.root.title(self.config.app_name)
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.root.minsize(self.config.min_width, self.config.min_height)

        self._build_ui()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=8)
        toolbar.grid(row=0, column=0, sticky="ew")

        ttk.Button(toolbar, text="New Node", command=self.create_node).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Edit Node", command=self.edit_selected_node).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Mark Done", command=self.mark_selected_done).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Delete Node", command=self.delete_selected_node).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            toolbar,
            text="Attach File",
            command=self.attach_file_to_selected_node,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Create Edge", command=self.begin_edge_mode).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Delete Edge", command=self.delete_selected_edge).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Edit Edge", command=self.edit_selected_edge).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Save", command=self.save_graph).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Load", command=self.load_graph).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Sample", command=self.load_sample_graph).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Recommend Next", command=self.recommend_next).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Agent", command=self.open_agent_dialog).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            toolbar,
            text="Capture Clipboard",
            command=self.capture_clipboard,
        ).pack(side="left", padx=(0, 8))

        self.focus_mode_var = tk.BooleanVar(
            value=self.context.graph.workspace.focus_mode
        )
        ttk.Checkbutton(
            toolbar,
            text="Focus Mode",
            variable=self.focus_mode_var,
            command=self.toggle_focus_mode,
        ).pack(side="left", padx=(0, 8))

        self.recommendation_var = tk.StringVar(value="Recommended: -")
        ttk.Label(toolbar, textvariable=self.recommendation_var).pack(
            side="left", padx=(16, 0)
        )

        self.canvas = GraphCanvas(self.root, self.context)
        self.canvas.grid(row=1, column=0, sticky="nsew")

        self.status_var = tk.StringVar(value=self.status_message)
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            padding=(8, 4),
        ).grid(row=2, column=0, sticky="ew")
        self._refresh_status_bar()

    def create_node(self) -> None:
        dialog = NodeDialog(self.root)
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            x, y = self._next_node_position()
            self.context.graph_service.create_node(
                title=str(dialog.result["title"]),
                description=str(dialog.result["description"]),
                node_type=dialog.result["node_type"],
                status=dialog.result["status"],
                priority=int(dialog.result["priority"]),
                estimated_minutes=int(dialog.result["estimated_minutes"]),
                repeat_type=dialog.result["repeat_type"],
                next_due_at=str(dialog.result["next_due_at"]) or None,
                streak=int(dialog.result["streak"]),
                x=x,
                y=y,
            )
            self.canvas.redraw()
            self._set_status("Node created")
        except PetFlowError as exc:
            messagebox.showerror("Create node failed", str(exc), parent=self.root)

    def edit_selected_node(self) -> None:
        self.canvas.edit_selected_node()

    def mark_selected_done(self) -> None:
        self.canvas.mark_selected_node_status(NodeStatus.DONE)
        self._update_recommendation_label()
        self.canvas.redraw()
        self._set_status("Node marked done")

    def delete_selected_node(self) -> None:
        self.canvas.delete_selected_node()

    def begin_edge_mode(self) -> None:
        self.canvas.begin_edge_mode()

    def delete_selected_edge(self) -> None:
        self.canvas.delete_selected_edge()

    def edit_selected_edge(self) -> None:
        self.canvas.edit_selected_edge()

    def save_graph(self) -> None:
        try:
            self.context.storage_service.save_graph(
                self.context.graph, DEFAULT_GRAPH_PATH
            )
            self._set_status(f"Saved: {DEFAULT_GRAPH_PATH.name}")
        except PetFlowError as exc:
            messagebox.showerror("Save failed", str(exc), parent=self.root)

    def load_graph(self) -> None:
        try:
            graph = self.context.storage_service.load_graph(DEFAULT_GRAPH_PATH)
            self.context = AppContext.create(graph)
            self.canvas.set_context(self.context)
            self.focus_mode_var.set(self.context.graph.workspace.focus_mode)
            self._update_recommendation_label()
            self._sync_pet_to_recommendation()
            self._set_status(f"Loaded: {DEFAULT_GRAPH_PATH.name}")
        except PetFlowError as exc:
            messagebox.showerror("Load failed", str(exc), parent=self.root)

    def load_sample_graph(self) -> None:
        try:
            sample_path = DEFAULT_GRAPH_PATH.parent / "sample_graph.json"
            graph = self.context.storage_service.load_graph(sample_path)
            self.context = AppContext.create(graph)
            self.canvas.set_context(self.context)
            self.focus_mode_var.set(self.context.graph.workspace.focus_mode)
            self._update_recommendation_label()
            self._sync_pet_to_recommendation()
            self._set_status("Loaded sample graph")
        except PetFlowError as exc:
            messagebox.showerror("Sample load failed", str(exc), parent=self.root)

    def recommend_next(self) -> None:
        node = self.context.recommendation_engine.recommend_next(self.context.graph)
        if node is None:
            self.recommendation_var.set("Recommended: -")
            messagebox.showinfo("Recommend Next", "No available node.", parent=self.root)
            return
        self.canvas.select_node(node.id)
        self.context.pet_service.react_to_recommendation(node)
        self.canvas.redraw()
        self.recommendation_var.set(f"Recommended: {node.title}")
        self._set_status(f"Recommended: {node.title}")
        messagebox.showinfo(
            "Recommend Next",
            f"Next: {node.title}\nStatus: {node.status.value}\nPriority: P{node.priority}",
            parent=self.root,
        )

    def open_agent_dialog(self, node_id: str | None = None) -> None:
        dialog = AgentDialog(self.root, self.context, node_id=node_id)
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        self.canvas.redraw()
        self._update_recommendation_label()
        self._sync_pet_to_recommendation()
        self._set_status("Agent proposal applied")

    def capture_clipboard(self) -> None:
        capture = self.clipboard_watcher.capture_once(self.root.clipboard_get)
        if capture is None:
            self._set_status("Clipboard: no usable content")
            messagebox.showinfo("Clipboard", "No usable clipboard content.", parent=self.root)
            return
        x, y = self._next_node_position()
        resource_path = capture.content if capture.resource_type == "url" else ""
        node = self.context.graph_service.create_resource_node(
            title=capture.title,
            resource_type=capture.resource_type,
            resource_path=resource_path,
            description=capture.content,
            x=x,
            y=y,
        )
        self.canvas.select_node(node.id)
        self.canvas.redraw()
        self._set_status(f"Clipboard captured: {node.title}")

    def attach_file_to_selected_node(self) -> None:
        node_id = self.canvas.selected_node_id()
        if node_id is None:
            messagebox.showinfo("Attach File", "Select a node first.", parent=self.root)
            return
        path = filedialog.askopenfilename(parent=self.root)
        if not path:
            return
        try:
            node = self.context.graph_service.add_node_attachment(node_id, path)
            self.canvas.redraw()
            self._set_status(f"Attached file to {node.title}")
        except PetFlowError as exc:
            messagebox.showerror("Attach failed", str(exc), parent=self.root)

    def toggle_focus_mode(self) -> None:
        enabled = bool(self.focus_mode_var.get())
        self.context.graph.workspace.focus_mode = enabled
        if enabled:
            self.focus_started_at = datetime.now()
            self._set_status("Focus mode: on")
        else:
            self.focus_started_at = None
            self._set_status("Focus mode: off")

    def _update_recommendation_label(self) -> None:
        node = self.context.recommendation_engine.recommend_next(self.context.graph)
        if node is None:
            self.recommendation_var.set("Recommended: -")
            return
        self.recommendation_var.set(f"Recommended: {node.title}")

    def _sync_pet_to_recommendation(self) -> None:
        node = self.context.recommendation_engine.recommend_next(self.context.graph)
        self.context.pet_service.react_to_recommendation(node)
        self.canvas.redraw()

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.status_var.set(self._status_text())

    def _refresh_status_bar(self) -> None:
        self.status_var.set(self._status_text())
        self.status_after_id = self.root.after(1000, self._refresh_status_bar)

    def _status_text(self) -> str:
        parts = [
            self.status_message,
            f"Nodes: {len(self.context.graph.nodes)}",
            f"Edges: {len(self.context.graph.edges)}",
        ]
        current_node = self.context.graph.get_node(
            self.context.graph.workspace.current_node_id or ""
        )
        if current_node is not None:
            parts.append(f"Current: {current_node.title}")
        if self.context.graph.workspace.focus_mode:
            parts.append(f"Focus: {self._focus_elapsed_text()}")
        else:
            parts.append("Focus: off")
        return " | ".join(parts)

    def _focus_elapsed_text(self) -> str:
        if self.focus_started_at is None:
            return "on"
        elapsed = datetime.now() - self.focus_started_at
        total_seconds = max(0, int(elapsed.total_seconds()))
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _next_node_position(self) -> tuple[float, float]:
        count = len(self.context.graph.nodes)
        column = count % 4
        row = count // 4
        return 120.0 + column * 210.0, 120.0 + row * 120.0

    def run(self) -> None:
        self.root.mainloop()
