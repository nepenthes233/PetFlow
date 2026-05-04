from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from petflow.domain.entities import PetState
from petflow.domain.enums import PetStateType

CoordinateTransform = Callable[[float, float], tuple[float, float]]


class PetView:
    def __init__(
        self,
        canvas: tk.Canvas,
        to_screen: CoordinateTransform | None = None,
    ) -> None:
        self.canvas = canvas
        self.to_screen = to_screen or (lambda x, y: (x, y))

    def draw(self, pet: PetState) -> None:
        if not pet.visible:
            return
        x, y = self.to_screen(pet.x or 40.0, pet.y or 40.0)
        fill = self._fill_for_state(pet.state)
        outline = "#334155"

        self.canvas.create_oval(
            x,
            y,
            x + 44,
            y + 38,
            fill=fill,
            outline=outline,
            width=2,
            tags=("pet",),
        )
        self.canvas.create_oval(
            x + 10,
            y + 12,
            x + 15,
            y + 17,
            fill="#0f172a",
            outline="",
            tags=("pet",),
        )
        self.canvas.create_oval(
            x + 29,
            y + 12,
            x + 34,
            y + 17,
            fill="#0f172a",
            outline="",
            tags=("pet",),
        )
        self.canvas.create_arc(
            x + 13,
            y + 14,
            x + 31,
            y + 30,
            start=200,
            extent=140,
            style=tk.ARC,
            outline="#0f172a",
            width=2,
            tags=("pet",),
        )
        self.canvas.create_text(
            x + 22,
            y + 47,
            text=pet.state.value,
            fill="#334155",
            font=("Arial", 8, "bold"),
            tags=("pet",),
        )
        if pet.speech:
            self._draw_bubble(x + 52, y - 6, pet.speech)

    def _draw_bubble(self, x: float, y: float, text: str) -> None:
        display_text = self._fit_text(text, 34)
        width = max(92, min(230, len(display_text) * 7 + 24))
        height = 34
        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill="#ffffff",
            outline="#94a3b8",
            width=1,
            tags=("pet",),
        )
        self.canvas.create_polygon(
            x,
            y + 18,
            x - 10,
            y + 24,
            x,
            y + 28,
            fill="#ffffff",
            outline="#94a3b8",
            tags=("pet",),
        )
        self.canvas.create_text(
            x + 10,
            y + 17,
            text=display_text,
            anchor="w",
            fill="#0f172a",
            font=("Arial", 9),
            tags=("pet",),
        )

    @staticmethod
    def _fit_text(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "..."

    @staticmethod
    def _fill_for_state(state: PetStateType) -> str:
        if state == PetStateType.HAPPY:
            return "#bbf7d0"
        if state == PetStateType.THINK:
            return "#ddd6fe"
        if state == PetStateType.MOVE:
            return "#bfdbfe"
        if state == PetStateType.ANGRY:
            return "#fecaca"
        if state == PetStateType.SLEEP:
            return "#e2e8f0"
        return "#fde68a"
