from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from petflow.app.app_context import AppContext
from petflow.config import AppConfig, DEFAULT_GRAPH_PATH
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

        ttk.Button(toolbar, text="New Node", command=self._placeholder).pack(
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

    def _placeholder(self) -> None:
        return None

    def save_graph(self) -> None:
        self.context.storage_service.save_graph(self.context.graph, DEFAULT_GRAPH_PATH)

    def load_graph(self) -> None:
        graph = self.context.storage_service.load_graph(DEFAULT_GRAPH_PATH)
        self.context = AppContext.create(graph)
        self.canvas.set_context(self.context)

    def run(self) -> None:
        self.root.mainloop()
