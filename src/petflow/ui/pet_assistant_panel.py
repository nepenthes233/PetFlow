from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from petflow.domain.entities import PetState
from petflow.ui.pet_view import PetView


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
            width=270,
            bg="#FFFFFF",
            highlightthickness=1,
            highlightbackground="#E5E7EB",
        )
        self.grid_propagate(False)
        self.font_family = font_family
        self.on_submit = on_submit
        self._busy = False

        controls = tk.Frame(self, bg="#FFFFFF")
        controls.pack(fill="x", padx=12, pady=(7, 0))
        if on_collapse is not None:
            tk.Button(
                controls,
                text="Hide",
                command=on_collapse,
                bg="#FFFFFF",
                fg="#6B7280",
                activebackground="#F3F4F6",
                relief="flat",
                borderwidth=0,
                cursor="hand2",
                font=(font_family, 8),
            ).pack(side="right")

        pet_canvas = tk.Canvas(
            self,
            width=PetView.WIDTH,
            height=PetView.HEIGHT,
            bg="#FFFFFF",
            highlightthickness=0,
        )
        pet_canvas.pack(padx=20, pady=(2, 3))
        self.pet_view = PetView(pet_canvas, font_family=font_family)

        tk.Label(
            self,
            text="PLAN WITH COMPANION",
            bg="#FFFFFF",
            fg="#6B7280",
            anchor="w",
            font=(font_family, 9, "bold"),
        ).pack(fill="x", padx=16, pady=(0, 6))

        self._history = tk.Text(
            self,
            height=10,
            wrap="word",
            bg="#F8FAFC",
            fg="#374151",
            relief="flat",
            borderwidth=0,
            padx=9,
            pady=8,
            font=(font_family, 9),
            state="disabled",
        )
        self._history.pack(fill="x", padx=12, pady=(0, 8))
        self.add_message("Pet", "Describe a goal. I will turn it into a task flow.")

        self._input = tk.Text(
            self,
            height=4,
            wrap="word",
            bg="#FFFFFF",
            fg="#111827",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=7,
            font=(font_family, 9),
        )
        self._input.pack(fill="x", padx=12, pady=(0, 8))
        self._input.bind("<Control-Return>", lambda _event: self._submit("plan"))

        actions = tk.Frame(self, bg="#FFFFFF")
        actions.pack(fill="x", padx=12, pady=(0, 12))
        self._status_var = tk.StringVar(value="Ask a question or plan a flow")
        tk.Label(
            actions,
            textvariable=self._status_var,
            bg="#FFFFFF",
            fg="#94A3B8",
            anchor="w",
            font=(font_family, 8),
        ).pack(side="left")
        self._plan_button = tk.Button(
            actions,
            text="Plan Flow",
            command=lambda: self._submit("plan"),
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            relief="flat",
            borderwidth=0,
            padx=11,
            pady=6,
            font=(font_family, 9, "bold"),
            cursor="hand2",
        )
        self._plan_button.pack(side="right")
        self._ask_button = tk.Button(
            actions,
            text="Ask",
            command=lambda: self._submit("chat"),
            bg="#FFFFFF",
            fg="#2563EB",
            activebackground="#EFF6FF",
            activeforeground="#1D4ED8",
            relief="solid",
            borderwidth=1,
            padx=11,
            pady=6,
            font=(font_family, 9, "bold"),
            cursor="hand2",
        )
        self._ask_button.pack(side="right", padx=(0, 6))

    def render_pet(self, pet: PetState, reaction: str | None = None) -> None:
        self.pet_view.draw(pet, reaction)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._plan_button.configure(
            state="disabled" if busy else "normal",
            bg="#93C5FD" if busy else "#2563EB",
        )
        self._ask_button.configure(state="disabled" if busy else "normal")
        self._status_var.set("Waiting for agent..." if busy else "Ask or plan a flow")

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
