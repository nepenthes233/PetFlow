from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from petflow.app.app_context import AppContext
from petflow.config import DEFAULT_GRAPH_PATH, AppConfig
from petflow.domain.enums import NodeStatus, PetStateType
from petflow.domain.exceptions import PetFlowError
from petflow.system.clipboard_watcher import ClipboardWatcher
from petflow.system.focus_monitor import FocusMonitor
from petflow.ui.agent_dialog import AgentDialog
from petflow.ui.dialogs import NodeDialog
from petflow.ui.graph_canvas import GraphCanvas
from petflow.ui.settings_dialog import SettingsDialog


class MainWindow:
    def __init__(self) -> None:
        self.config = AppConfig()
        self.context = AppContext.create()
        self.graph = self.context.storage_service.load_graph(DEFAULT_GRAPH_PATH)
        self.context = AppContext.create(self.graph)
        self.clipboard_watcher = ClipboardWatcher()
        self.focus_monitor = FocusMonitor()
        self.focus_started_at: datetime | None = None
        self.status_message = "Ready"
        self.status_after_id: str | None = None
        self.toolbar: tk.Frame | None = None
        self.toolbar_items: list[tuple[tk.Widget, tuple[int, int], str]] = []
        self.toolbar_layout_after_id: str | None = None
        self.toolbar_layout_width: int | None = None

        self.root = tk.Tk()
        self.root.title(self.config.app_name)
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.root.minsize(self.config.min_width, self.config.min_height)

        self._build_ui()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = tk.Frame(self.root, width=self.config.window_width, height=80)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_propagate(False)
        self.toolbar = toolbar

        self._add_toolbar_item(
            ttk.Button(toolbar, text="New Node", command=self.create_node)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Edit Node", command=self.edit_selected_node)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Mark Done", command=self.mark_selected_done)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Delete Node", command=self.delete_selected_node)
        )
        self._add_toolbar_item(
            ttk.Button(
                toolbar,
                text="Attach File",
                command=self.attach_file_to_selected_node,
            )
        )
        self._add_toolbar_item(
            ttk.Button(
                toolbar,
                text="Copy Resource",
                command=self.copy_selected_resource,
            )
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Create Edge", command=self.begin_edge_mode)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Delete Edge", command=self.delete_selected_edge)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Edit Edge", command=self.edit_selected_edge)
        )
        self._add_toolbar_item(ttk.Button(toolbar, text="Save", command=self.save_graph))
        self._add_toolbar_item(ttk.Button(toolbar, text="Load", command=self.load_graph))
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Sample", command=self.load_sample_graph)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Layout", command=self.layout_graph)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Zoom In", command=self.zoom_in)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Zoom Out", command=self.zoom_out)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Reset View", command=self.reset_view)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Recommend Next", command=self.recommend_next)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Agent", command=self.open_agent_dialog)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Review", command=self.show_review)
        )
        self._add_toolbar_item(
            ttk.Button(toolbar, text="Settings", command=self.open_settings_dialog)
        )
        self._add_toolbar_item(
            ttk.Button(
                toolbar,
                text="Capture Clipboard",
                command=self.capture_clipboard,
            )
        )

        self.focus_mode_var = tk.BooleanVar(
            value=self.context.graph.workspace.focus_mode
        )
        self._add_toolbar_item(
            ttk.Checkbutton(
                toolbar,
                text="Focus Mode",
                variable=self.focus_mode_var,
                command=self.toggle_focus_mode,
            )
        )

        self.recommendation_var = tk.StringVar(value="Recommended: -")
        self.recommendation_label = ttk.Label(
            toolbar,
            textvariable=self.recommendation_var,
            wraplength=320,
        )
        self._add_toolbar_item(
            self.recommendation_label,
            padx=(16, 0),
            sticky="w",
        )
        toolbar.bind("<Configure>", self._schedule_toolbar_layout)
        self.root.after_idle(self._layout_toolbar)

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

    def _add_toolbar_item(
        self,
        widget: tk.Widget,
        padx: tuple[int, int] = (0, 8),
        sticky: str = "w",
    ) -> None:
        self.toolbar_items.append((widget, padx, sticky))

    def _schedule_toolbar_layout(self, event: tk.Event[tk.Frame] | None = None) -> None:
        if event is not None and self.toolbar_layout_width == event.width:
            return
        if self.toolbar_layout_after_id is not None:
            return
        self.toolbar_layout_after_id = self.root.after(50, self._layout_toolbar)

    def _layout_toolbar(self) -> None:
        self.toolbar_layout_after_id = None
        if self.toolbar is None:
            return

        width = self.toolbar.winfo_width()
        if width <= 1:
            width = self.root.winfo_width()
        if width <= 1:
            width = self.config.window_width
        self.toolbar_layout_width = width
        margin_x = 8
        margin_y = 8
        row_gap = 6
        available_width = max(160, width - margin_x * 2)
        self.recommendation_label.configure(
            wraplength=max(120, min(320, available_width // 3))
        )

        rows: list[list[tuple[tk.Widget, tuple[int, int], str]]] = [[]]
        row_width = 0
        for widget, padx, sticky in self.toolbar_items:
            item_width = widget.winfo_reqwidth() + padx[0] + padx[1]
            if rows[-1] and row_width + item_width > available_width:
                rows.append([])
                row_width = 0
            rows[-1].append((widget, padx, sticky))
            row_width += item_width

        for widget, _padx, _sticky in self.toolbar_items:
            widget.place_forget()

        y = margin_y
        for row_index, row_items in enumerate(rows):
            row_height = max(widget.winfo_reqheight() for widget, _padx, _sticky in row_items)
            x = margin_x
            for widget, padx, _sticky in row_items:
                x += padx[0]
                widget.place(
                    x=x,
                    y=y,
                    width=widget.winfo_reqwidth(),
                    height=widget.winfo_reqheight(),
                )
                x += widget.winfo_reqwidth() + padx[1]
            y += row_height + row_gap
        self.toolbar.configure(width=width, height=y + margin_y - row_gap)
        self.root.rowconfigure(0, minsize=y + margin_y - row_gap)

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
                actual_minutes=int(dialog.result["actual_minutes"]),
                tags=dialog.result["tags"],
                resource_type=dialog.result["resource_type"],
                resource_path=str(dialog.result["resource_path"]),
                checklist=dialog.result["checklist"],
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

    def layout_graph(self) -> None:
        self.context.graph_layout_service.apply_grid_layout(self.context.graph_service)
        self.canvas.redraw()
        self._set_status("Graph layout refreshed")

    def zoom_in(self) -> None:
        self.canvas.zoom_in()
        self._set_status(f"Zoom: {self.context.graph.workspace.zoom:.0%}")

    def zoom_out(self) -> None:
        self.canvas.zoom_out()
        self._set_status(f"Zoom: {self.context.graph.workspace.zoom:.0%}")

    def reset_view(self) -> None:
        self.canvas.reset_view()
        self._set_status("View reset")

    def recommend_next(self) -> None:
        node = self.context.recommendation_engine.recommend_next(self.context.graph)
        if node is None:
            self.recommendation_var.set("Recommended: -")
            self._schedule_toolbar_layout()
            messagebox.showinfo("Recommend Next", "No available node.", parent=self.root)
            return
        reason = self.context.recommendation_engine.recommend_reason(
            self.context.graph,
            node,
        )
        self.canvas.select_node(node.id)
        self.context.pet_service.react_to_recommendation(node)
        self.canvas.redraw()
        self.recommendation_var.set(f"Recommended: {node.title} | {reason}")
        self._schedule_toolbar_layout()
        self._set_status(f"Recommended: {node.title}")
        messagebox.showinfo(
            "Recommend Next",
            f"Next: {node.title}\nReason: {reason}\nStatus: {node.status.value}\nPriority: P{node.priority}",
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

    def open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.root)
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        self._set_status("Settings saved")

    def show_review(self) -> None:
        summary = self.context.review_service.summary_text(self.context.graph)
        messagebox.showinfo("Review", summary, parent=self.root)
        self._set_status("Review generated")

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

    def copy_selected_resource(self) -> None:
        node_id = self.canvas.selected_node_id()
        if node_id is None:
            messagebox.showinfo(
                "Copy Resource", "Select a resource node first.", parent=self.root
            )
            return
        node = self.context.graph.get_node(node_id)
        if node is None:
            return
        try:
            value = self.context.resource_service.resource_text(node)
        except PetFlowError as exc:
            messagebox.showerror("Copy resource failed", str(exc), parent=self.root)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self._set_status(f"Copied resource: {node.title}")

    def toggle_focus_mode(self) -> None:
        enabled = bool(self.focus_mode_var.get())
        self.context.graph.workspace.focus_mode = enabled
        if enabled:
            self.focus_started_at = datetime.now()
            current_node = self.context.graph.get_node(
                self.context.graph.workspace.current_node_id or ""
            )
            if current_node is None:
                self.context.graph.pet.state = PetStateType.ANGRY
                self.context.graph.pet.speech = "Select a focus node first."
                self.context.graph.pet.visible = True
                self.context.graph.pet.touch()
                self.canvas.redraw()
            else:
                self.context.pet_service.move_to_node(
                    current_node.id,
                    speech=f"Focus: {current_node.title}",
                )
                self.canvas.redraw()
            self._set_status("Focus mode: on")
        else:
            self.focus_started_at = None
            self._set_status("Focus mode: off")

    def _update_recommendation_label(self) -> None:
        node = self.context.recommendation_engine.recommend_next(self.context.graph)
        if node is None:
            self.recommendation_var.set("Recommended: -")
            self._schedule_toolbar_layout()
            return
        reason = self.context.recommendation_engine.recommend_reason(
            self.context.graph,
            node,
        )
        self.recommendation_var.set(f"Recommended: {node.title} | {reason}")
        self._schedule_toolbar_layout()

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
            window_title = self.focus_monitor.current_window_title()
            if window_title:
                parts.append(f"Window: {window_title[:32]}")
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
