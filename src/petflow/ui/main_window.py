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
        ttk.Button(toolbar, text="Save", command=self.save_graph).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Load", command=self.load_graph).pack(
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
            self.context.graph_service.create_node(
                title=str(dialog.result["title"]),
                description=str(dialog.result["description"]),
                node_type=dialog.result["node_type"],
                status=dialog.result["status"],
                priority=int(dialog.result["priority"]),
                estimated_minutes=int(dialog.result["estimated_minutes"]),
                x=160,
                y=140,
            )
            self.canvas.redraw()
        except PetFlowError as exc:
            messagebox.showerror("Create node failed", str(exc), parent=self.root)

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

    def run(self) -> None:
        self.root.mainloop()
