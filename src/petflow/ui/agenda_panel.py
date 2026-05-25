from __future__ import annotations

from datetime import date
import tkinter as tk
from typing import Callable

from petflow.domain.entities import Node
from petflow.domain.graph import GraphModel
from petflow.services.agenda_service import AgendaDay, AgendaService


class AgendaPanel(tk.Frame):
    BG = "#FFFFFF"
    TEXT = "#111827"
    MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    ACCENT = "#2563EB"

    def __init__(
        self,
        master: tk.Misc,
        agenda_service: AgendaService,
        on_select_node: Callable[[str], None],
        font_family: str,
        on_collapse: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            bg=self.BG,
            width=280,
            padx=18,
            pady=20,
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        self.grid_propagate(False)
        self.agenda_service = agenda_service
        self.on_select_node = on_select_node
        self.font_family = font_family
        self.on_collapse = on_collapse
        self._expanded: set[date] = set()
        self._days: list[AgendaDay] = []

        heading = tk.Frame(self, bg=self.BG)
        heading.pack(fill="x")
        tk.Label(
            heading,
            text="UPCOMING",
            bg=self.BG,
            fg=self.ACCENT,
            font=(font_family, 9, "bold"),
        ).pack(side="left", anchor="w")
        if on_collapse is not None:
            tk.Button(
                heading,
                text="Hide",
                command=on_collapse,
                bg=self.BG,
                fg=self.MUTED,
                activebackground="#F3F4F6",
                relief="flat",
                borderwidth=0,
                cursor="hand2",
                font=(font_family, 8),
            ).pack(side="right")
        tk.Label(
            self,
            text="Next 7 days",
            bg=self.BG,
            fg=self.TEXT,
            font=(font_family, 18, "bold"),
        ).pack(anchor="w", pady=(2, 2))
        tk.Frame(self, bg=self.BORDER, height=1).pack(fill="x", pady=(15, 8))

        list_shell = tk.Frame(self, bg=self.BG)
        list_shell.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(
            list_shell,
            bg=self.BG,
            highlightthickness=0,
            width=238,
        )
        scrollbar = tk.Scrollbar(
            list_shell,
            orient="vertical",
            command=self._canvas.yview,
            width=8,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        self._list = tk.Frame(self._canvas, bg=self.BG)
        self._window = self._canvas.create_window(
            (0, 0), window=self._list, anchor="nw"
        )
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._list.bind("<Configure>", self._sync_scroll_region)
        self._canvas.bind("<Configure>", self._resize_list)
        self._canvas.bind("<MouseWheel>", self._scroll)
        self._list.bind("<MouseWheel>", self._scroll)

    def refresh(self, graph: GraphModel) -> None:
        self._days = self.agenda_service.upcoming_days(graph)
        today = self._days[0].date if self._days else None
        if not self._expanded and today is not None:
            self._expanded.add(today)
        self._render()

    def _render(self) -> None:
        for child in self._list.winfo_children():
            child.destroy()
        for day in self._days:
            self._draw_day(day)

    def _draw_day(self, day: AgendaDay) -> None:
        open_day = day.date in self._expanded
        card = tk.Frame(self._list, bg=self.BG)
        card.pack(fill="x")
        label = self._day_label(day.date)
        summary = str(len(day.nodes))
        header = tk.Frame(card, bg=self.BG, pady=4)
        header.pack(fill="x")
        day_button = tk.Button(
            header,
            text=f"{'-' if open_day else '+'}  {label}",
            command=lambda target=day.date: self._toggle(target),
            anchor="w",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            bg=self.BG,
            activebackground="#F3F4F6",
            fg=self.TEXT,
            font=(self.font_family, 10, "bold"),
            padx=0,
            pady=7,
        )
        day_button.pack(side="left", fill="x", expand=True)
        tk.Button(
            header,
            text=summary,
            command=lambda target=day.date: self._toggle(target),
            anchor="e",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            bg=self.BG,
            activebackground="#F3F4F6",
            fg=self.MUTED,
            font=(self.font_family, 10),
            padx=5,
            pady=7,
        ).pack(side="right")
        if open_day and not day.nodes:
            tk.Label(
                card,
                text="Nothing scheduled",
                bg=self.BG,
                fg=self.MUTED,
                anchor="w",
                font=(self.font_family, 9),
                padx=18,
                pady=3,
            ).pack(fill="x", pady=(0, 6))
        elif open_day:
            for node in day.nodes:
                self._draw_node(card, node)
        tk.Frame(card, bg=self.BORDER, height=1).pack(fill="x")

    def _draw_node(self, card: tk.Frame, node: Node) -> None:
        text = f"P{node.priority}  {node.title}"
        button = tk.Button(
            card,
            text=text,
            command=lambda node_id=node.id: self.on_select_node(node_id),
            anchor="w",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            padx=18,
            pady=3,
            bg=self.BG,
            activebackground="#EFF6FF",
            fg=self.TEXT,
            font=(self.font_family, 10),
        )
        button.pack(fill="x")
        tk.Label(
            card,
            text=f"{node.status.value.capitalize()}  ·  {node.estimated_minutes} min",
            bg=self.BG,
            fg=self.MUTED,
            anchor="w",
            padx=18,
            font=(self.font_family, 8),
        ).pack(fill="x", pady=(0, 5))

    def _toggle(self, day: date) -> None:
        if day in self._expanded:
            self._expanded.remove(day)
        else:
            self._expanded.add(day)
        self._render()

    @staticmethod
    def _day_label(day: date) -> str:
        if day == date.today():
            return "Today"
        return day.strftime("%a  %m/%d")

    def _sync_scroll_region(self, _event: tk.Event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _resize_list(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._window, width=event.width)

    def _scroll(self, event: tk.Event) -> str:
        self._canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"
