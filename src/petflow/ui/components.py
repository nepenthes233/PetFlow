from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from petflow.ui.theme import (
    BORDER,
    BORDER_STRONG,
    PRIMARY,
    PRIMARY_HOVER,
    PRIMARY_SOFT,
    SURFACE,
    SURFACE_SUBTLE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class TextButton(tk.Button):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        font_family: str,
        *,
        variant: str = "secondary",
        width: int | None = None,
    ) -> None:
        self.variant = variant
        palette = self._palette(variant)
        super().__init__(
            master,
            text=text,
            command=command,
            width=width or 0,
            bg=palette["bg"],
            fg=palette["fg"],
            activebackground=palette["hover"],
            activeforeground=palette["active_fg"],
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=palette["border"],
            highlightcolor=palette["border"],
            padx=14,
            pady=8,
            cursor="hand2",
            takefocus=0,
            font=(font_family, 10, "bold" if variant == "primary" else "normal"),
        )
        self._normal_bg = palette["bg"]
        self._hover_bg = palette["hover"]
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")

    @staticmethod
    def _palette(variant: str) -> dict[str, str]:
        if variant == "primary":
            return {
                "bg": PRIMARY,
                "fg": SURFACE,
                "hover": PRIMARY_HOVER,
                "active_fg": SURFACE,
                "border": PRIMARY,
            }
        if variant == "ghost":
            return {
                "bg": SURFACE,
                "fg": TEXT_SECONDARY,
                "hover": SURFACE_SUBTLE,
                "active_fg": TEXT_PRIMARY,
                "border": SURFACE,
            }
        return {
            "bg": SURFACE,
            "fg": TEXT_SECONDARY,
            "hover": SURFACE_SUBTLE,
            "active_fg": TEXT_PRIMARY,
            "border": BORDER,
        }

    def _on_enter(self, _event: tk.Event) -> None:
        if str(self.cget("state")) == "normal":
            self.configure(bg=self._hover_bg)

    def _on_leave(self, _event: tk.Event) -> None:
        self.configure(bg=self._normal_bg)


class Chip(tk.Label):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        font_family: str,
        *,
        selected: bool = False,
    ) -> None:
        super().__init__(
            master,
            text=text,
            bg=PRIMARY_SOFT if selected else SURFACE_SUBTLE,
            fg=PRIMARY if selected else TEXT_SECONDARY,
            padx=10,
            pady=4,
            font=(font_family, 9, "bold" if selected else "normal"),
            highlightthickness=1,
            highlightbackground=BORDER_STRONG if selected else BORDER,
        )
