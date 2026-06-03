from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import tkinter as tk
from typing import Callable

from petflow.domain.entities import Node
from petflow.domain.graph import GraphModel
from petflow.services.agenda_service import AgendaDay, AgendaService
from petflow.ui.icon_button import IconButton
from petflow.ui.theme import (
    BORDER,
    PRIMARY,
    PRIMARY_SOFT,
    SURFACE,
    SURFACE_SUBTLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


@dataclass(frozen=True, slots=True)
class SavedGraphTasks:
    name: str
    nodes: tuple[Node, ...]


class AgendaPanel(tk.Frame):
    BG = SURFACE
    TEXT = TEXT_PRIMARY
    MUTED = TEXT_MUTED
    BORDER = BORDER
    ACCENT = PRIMARY

    def __init__(
        self,
        master: tk.Misc,
        agenda_service: AgendaService,
        on_select_node: Callable[[str], None],
        font_family: str,
        on_collapse: Callable[[], None] | None = None,
        on_refresh: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            bg=self.BG,
            width=280,
            padx=16,
            pady=16,
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        self.grid_propagate(False)
        self.agenda_service = agenda_service
        self.on_select_node = on_select_node
        self.font_family = font_family
        self.on_collapse = on_collapse
        self.on_refresh = on_refresh
        self._expanded: set[date] = set()
        self._days: list[AgendaDay] = []
        self._saved_graphs: list[SavedGraphTasks] = []
        self._saved_by_day: dict[date, list[tuple[str, Node]]] = {}

        heading = tk.Frame(self, bg=self.BG)
        heading.pack(fill="x")
        tk.Label(
            heading,
            text="UPCOMING",
            bg=self.BG,
            fg=TEXT_MUTED,
            font=(font_family, 9, "bold"),
        ).pack(side="left", anchor="w")
        if on_collapse is not None:
            IconButton(
                heading,
                "hide",
                "Hide schedule panel",
                command=on_collapse,
                size=30,
            ).pack(side="right")
        if on_refresh is not None:
            IconButton(
                heading,
                "refresh",
                "Refresh schedule panel",
                command=on_refresh,
                size=30,
            ).pack(side="right", padx=(0, 4))
        tk.Label(
            self,
            text="Next 7 days",
            bg=self.BG,
            fg=self.TEXT,
            font=(font_family, 16, "bold"),
        ).pack(anchor="w", pady=(2, 0))
        tk.Frame(self, bg=self.BORDER, height=1).pack(fill="x", pady=(12, 8))

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
        self._canvas.bind("<Button-4>", self._scroll)
        self._canvas.bind("<Button-5>", self._scroll)
        self._list.bind("<MouseWheel>", self._scroll)
        self._list.bind("<Button-4>", self._scroll)
        self._list.bind("<Button-5>", self._scroll)

    def refresh(
        self,
        graph: GraphModel,
        saved_graphs: list[SavedGraphTasks] | None = None,
    ) -> None:
        self._days = self.agenda_service.upcoming_days(graph)
        self._saved_graphs = saved_graphs or []
        self._saved_by_day = self._group_saved_graph_tasks()
        today = self._days[0].date if self._days else None
        if not self._expanded and today is not None:
            self._expanded.add(today)
        self._render()

    def _render(self) -> None:
        for child in self._list.winfo_children():
            child.destroy()
        for day in self._days:
            self._draw_day(day)
        self._bind_scroll_to_descendants(self)

    def _group_saved_graph_tasks(self) -> dict[date, list[tuple[str, Node]]]:
        grouped: dict[date, list[tuple[str, Node]]] = {}
        for saved_graph in self._saved_graphs:
            graph = GraphModel(
                nodes={
                    f"{saved_graph.name}:{node.id}": node
                    for node in saved_graph.nodes
                }
            )
            scheduled_ids: set[str] = set()
            for day in self.agenda_service.upcoming_days(graph):
                for node in day.nodes:
                    grouped.setdefault(day.date, []).append((saved_graph.name, node))
                    scheduled_ids.add(node.id)
            for node in saved_graph.nodes:
                if node.id not in scheduled_ids:
                    grouped.setdefault(date.today(), []).append(
                        (saved_graph.name, node)
                    )
        return grouped

    def _draw_day(self, day: AgendaDay) -> None:
        open_day = day.date in self._expanded
        card = tk.Frame(self._list, bg=self.BG)
        card.pack(fill="x")
        label = self._day_label(day.date)
        saved_nodes = self._saved_by_day.get(day.date, [])
        summary = str(len(day.nodes) + len(saved_nodes))
        today = day.date == date.today()
        row_bg = PRIMARY_SOFT if today else self.BG
        label_fg = PRIMARY if today else TEXT_SECONDARY
        header = tk.Frame(card, bg=row_bg)
        header.pack(fill="x")
        day_button = tk.Button(
            header,
            text=f"{'-' if open_day else '+'}  {label}",
            command=lambda target=day.date: self._toggle(target),
            anchor="w",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            bg=row_bg,
            activebackground=SURFACE_SUBTLE,
            fg=label_fg,
            font=(self.font_family, 10, "bold" if today else "normal"),
            padx=8,
            pady=8,
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
            bg=row_bg,
            activebackground=SURFACE_SUBTLE,
            fg=TEXT_MUTED,
            font=(self.font_family, 9),
            padx=8,
            pady=8,
        ).pack(side="right")
        if open_day and not day.nodes and not saved_nodes:
            tk.Label(
                card,
                text="No scheduled tasks",
                bg=self.BG,
                fg="#94A3B8",
                anchor="w",
                font=(self.font_family, 9),
                padx=24,
                pady=6,
            ).pack(fill="x", pady=(0, 4))
        elif open_day:
            for node in day.nodes:
                self._draw_node(card, node)
            for graph_name, node in saved_nodes:
                self._draw_saved_day_node(card, graph_name, node)
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
            pady=4,
            bg=self.BG,
            activebackground=SURFACE_SUBTLE,
            fg=TEXT_SECONDARY,
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

    def _draw_saved_day_node(
        self,
        card: tk.Frame,
        graph_name: str,
        node: Node,
    ) -> None:
        tk.Label(
            card,
            text=f"P{node.priority}  {node.title}",
            bg=self.BG,
            fg=TEXT_SECONDARY,
            anchor="w",
            padx=18,
            pady=3,
            font=(self.font_family, 10),
        ).pack(fill="x")
        details = f"{graph_name}  ·  {node.type.value}  ·  {node.status.value}"
        tk.Label(
            card,
            text=details,
            bg=self.BG,
            fg=self.MUTED,
            anchor="w",
            padx=18,
            font=(self.font_family, 8),
        ).pack(fill="x", pady=(0, 4))

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
        number = getattr(event, "num", None)
        if number == 4:
            self._scroll_pixels(-48.0)
        elif number == 5:
            self._scroll_pixels(48.0)
        else:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return "break"
            if abs(delta) >= 120:
                pixels = -float(delta) / 120.0 * 48.0
            else:
                pixels = -float(delta) * 3.0
            self._scroll_pixels(pixels)
        return "break"

    def _bind_scroll_to_descendants(self, root: tk.Misc) -> None:
        try:
            root.bind("<MouseWheel>", self._scroll)
            root.bind("<Button-4>", self._scroll)
            root.bind("<Button-5>", self._scroll)
        except tk.TclError:
            return
        for child in root.winfo_children():
            self._bind_scroll_to_descendants(child)

    def _scroll_pixels(self, pixels: float) -> None:
        try:
            bbox = self._canvas.bbox("all")
            if bbox is None:
                return
            content_height = max(1.0, float(bbox[3] - bbox[1]))
            viewport_height = max(1.0, float(self._canvas.winfo_height()))
            scrollable_height = max(0.0, content_height - viewport_height)
            if scrollable_height <= 0:
                return
            top_fraction = float(self._canvas.yview()[0])
            top_pixel = top_fraction * scrollable_height
            target_pixel = max(0.0, min(scrollable_height, top_pixel + pixels))
            self._canvas.yview_moveto(target_pixel / scrollable_height)
        except tk.TclError:
            return
