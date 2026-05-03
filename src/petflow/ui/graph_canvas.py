from __future__ import annotations

import tkinter as tk

from petflow.app.app_context import AppContext


class GraphCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc, context: AppContext, **kwargs) -> None:
        super().__init__(master, bg="#f5f7fb", highlightthickness=0, **kwargs)
        self.context = context
        self._redraw()

    def set_context(self, context: AppContext) -> None:
        self.context = context
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        self.create_text(
            80,
            40,
            text="PetFlow canvas placeholder",
            anchor="w",
            fill="#334155",
            font=("Arial", 16, "bold"),
        )
        self.create_text(
            80,
            72,
            text="Next step: implement nodes, edges, drag, and dialogs.",
            anchor="w",
            fill="#64748b",
            font=("Arial", 11),
        )
