from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from petflow.app.app_context import AppContext
from petflow.config import DEFAULT_GRAPH_PATH, AppConfig
from petflow.domain.exceptions import PetFlowError
from petflow.ui.dialogs import NodeDialog
from petflow.ui.graph_canvas import GraphCanvas


class MainWindow:
    def __init__(self) -> None:
        self.config = AppConfig()
        self.context = AppContext.create()
        self.graph = self.context.storage_service.load_graph(DEFAULT_GRAPH_PATH)
        self.context = AppContext.create(self.graph)

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
        ttk.Button(toolbar, text="Delete Node", command=self.delete_selected_node).pack(
            side="left", padx=(0, 8)
        )
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

        self.canvas = GraphCanvas(self.root, self.context)
        self.canvas.grid(row=1, column=0, sticky="nsew")

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
                x=x,
                y=y,
            )
            self.canvas.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Create node failed", str(exc), parent=self.root)

    def edit_selected_node(self) -> None:
        self.canvas.edit_selected_node()

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
        except PetFlowError as exc:
            messagebox.showerror("Save failed", str(exc), parent=self.root)

    def load_graph(self) -> None:
        try:
            graph = self.context.storage_service.load_graph(DEFAULT_GRAPH_PATH)
            self.context = AppContext.create(graph)
            self.canvas.set_context(self.context)
        except PetFlowError as exc:
            messagebox.showerror("Load failed", str(exc), parent=self.root)

    def load_sample_graph(self) -> None:
        try:
            sample_path = DEFAULT_GRAPH_PATH.parent / "sample_graph.json"
            graph = self.context.storage_service.load_graph(sample_path)
            self.context = AppContext.create(graph)
            self.canvas.set_context(self.context)
        except PetFlowError as exc:
            messagebox.showerror("Sample load failed", str(exc), parent=self.root)

    def _next_node_position(self) -> tuple[float, float]:
        count = len(self.context.graph.nodes)
        column = count % 4
        row = count // 4
        return 120.0 + column * 210.0, 120.0 + row * 120.0

    def run(self) -> None:
        self.root.mainloop()
