from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from petflow.domain.entities import PetState
from petflow.ui.components import TextButton
from petflow.ui.icon_button import IconButton
from petflow.ui.pet_view import PetView
from petflow.ui.theme import (
    BACKGROUND,
    BORDER,
    SURFACE,
    SURFACE_SUBTLE,
    TEXT_FAINT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class PetAssistantPanel(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        font_family: str,
        on_submit: Callable[[str, str], None],
        on_collapse: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            width=300,
            bg=SURFACE,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.grid_propagate(False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self.font_family = font_family
        self.on_submit = on_submit
        self._busy = False

        controls = tk.Frame(self, bg=SURFACE)
        controls.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))
        tk.Label(
            controls,
            text="Companion",
            bg=SURFACE,
            fg=TEXT_PRIMARY,
            font=(font_family, 14, "bold"),
        ).pack(side="left")
        tk.Label(
            controls,
            text="Mission Copilot",
            bg=SURFACE_SUBTLE,
            fg=TEXT_MUTED,
            padx=8,
            pady=3,
            font=(font_family, 9),
        ).pack(side="left", padx=(8, 0))
        if on_collapse is not None:
            IconButton(
                controls,
                "hide",
                "Hide right panel",
                command=on_collapse,
            ).pack(side="right")

        pet_canvas = tk.Canvas(
            self,
            width=PetView.WIDTH,
            height=PetView.HEIGHT,
            bg=SURFACE,
            highlightthickness=0,
        )
        pet_canvas.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        self.pet_view = PetView(pet_canvas, font_family=font_family)

        tk.Label(
            self,
            text="Ask Companion to plan your next mission",
            bg=SURFACE,
            fg=TEXT_SECONDARY,
            anchor="w",
            font=(font_family, 10, "bold"),
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 6))

        self._history = tk.Text(
            self,
            height=10,
            wrap="word",
            bg=BACKGROUND,
            fg=TEXT_SECONDARY,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
            font=(font_family, 10),
            state="disabled",
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self._history.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.add_message("Companion", "Tell me a goal and I will build a mission map.")

        composer = tk.Frame(self, bg=SURFACE)
        composer.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        composer.columnconfigure(0, weight=1)

        self._input = tk.Text(
            composer,
            height=3,
            wrap="word",
            bg=SURFACE,
            fg=TEXT_PRIMARY,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=8,
            font=(font_family, 10),
            highlightthickness=1,
            highlightbackground=BORDER,
            insertbackground=TEXT_PRIMARY,
        )
        self._input.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._input.bind("<Control-Return>", lambda _event: self._submit("plan"))

        actions = tk.Frame(composer, bg=SURFACE)
        actions.grid(row=1, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        self._status_var = tk.StringVar(value="Ask a question or plan a mission")
        tk.Label(
            actions,
            textvariable=self._status_var,
            bg=SURFACE,
            fg=TEXT_FAINT,
            anchor="w",
            font=(font_family, 8),
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))
        button_row = tk.Frame(actions, bg=SURFACE)
        button_row.grid(row=1, column=0, sticky="ew")
        button_row.columnconfigure(0, weight=1)
        self._plan_button = TextButton(
            button_row,
            "Plan Flow",
            command=lambda: self._submit("plan"),
            font_family=font_family,
            variant="primary",
        )
        self._plan_button.grid(row=0, column=0, sticky="ew")
        self._ask_button = TextButton(
            button_row,
            "Ask",
            command=lambda: self._submit("chat"),
            font_family=font_family,
            variant="secondary",
        )
        self._ask_button.grid(row=1, column=0, sticky="ew", pady=(8, 0))

    def render_pet(self, pet: PetState, reaction: str | None = None) -> None:
        self.pet_view.draw(pet, reaction)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._plan_button.configure(state="disabled" if busy else "normal")
        self._ask_button.configure(state="disabled" if busy else "normal")
        self._status_var.set("Planning mission..." if busy else "Ask or plan a mission")

    def add_message(self, author: str, message: str) -> None:
        cleaned = " ".join(message.strip().split())
        if not cleaned:
            return
        self._history.configure(state="normal")
        current = self._history.get("1.0", tk.END).strip()
        prefix = "\n\n" if current else ""
        self._history.insert(tk.END, f"{prefix}{author}: {cleaned}")
        self._history.configure(state="disabled")
        self._history.see(tk.END)

    def _submit(self, mode: str) -> None:
        if self._busy:
            return
        message = self._input.get("1.0", tk.END).strip()
        if not message:
            self._status_var.set("Enter a planning request first")
            return
        self._input.delete("1.0", tk.END)
        self.on_submit(message, mode)
