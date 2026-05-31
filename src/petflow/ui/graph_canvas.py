from __future__ import annotations

from dataclasses import dataclass
from math import hypot
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox
from typing import Callable

from petflow.app.app_context import AppContext
from petflow.domain.entities import Edge, Node
from petflow.domain.enums import EdgeType, NodeStatus, NodeType
from petflow.domain.exceptions import PetFlowError
from petflow.ui.dialogs import EdgeDialog, NodeDialog
from petflow.ui.theme import (
    APP_BG,
    BORDER,
    BORDER_STRONG,
    CARD_BG_HOVER,
    DANGER,
    DANGER_SOFT,
    DARK_APP_BG,
    DARK_BORDER,
    DARK_PANEL_SOFT,
    DARK_SURFACE,
    DARK_SURFACE_HOVER,
    DARK_TEXT,
    DARK_MUTED,
    PINK,
    PINK_SOFT,
    PRIMARY,
    PRIMARY_SOFT,
    PRIMARY_TINT,
    PURPLE,
    PURPLE_SOFT,
    SUCCESS,
    SUCCESS_SOFT,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WARNING,
    WARNING_SOFT,
)

Point = tuple[float, float]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def sample_cubic_bezier(
    p0: Point, p1: Point, p2: Point, p3: Point, steps: int = 24
) -> list[Point]:
    points: list[Point] = []
    for index in range(steps + 1):
        value = index / steps
        inverse = 1.0 - value
        points.append(
            (
                inverse**3 * p0[0]
                + 3 * inverse**2 * value * p1[0]
                + 3 * inverse * value**2 * p2[0]
                + value**3 * p3[0],
                inverse**3 * p0[1]
                + 3 * inverse**2 * value * p1[1]
                + 3 * inverse * value**2 * p2[1]
                + value**3 * p3[1],
            )
        )
    return points


def path_length(points: list[Point]) -> float:
    return sum(
        hypot(end[0] - start[0], end[1] - start[1])
        for start, end in zip(points, points[1:])
    )


def point_at_distance(points: list[Point], distance: float) -> Point:
    if not points:
        return (0.0, 0.0)
    remaining = max(0.0, distance)
    for start, end in zip(points, points[1:]):
        segment = hypot(end[0] - start[0], end[1] - start[1])
        if segment == 0:
            continue
        if remaining <= segment:
            ratio = remaining / segment
            return (
                start[0] + (end[0] - start[0]) * ratio,
                start[1] + (end[1] - start[1]) * ratio,
            )
        remaining -= segment
    return points[-1]


def extract_subpath(
    points: list[Point], start_distance: float, end_distance: float
) -> list[Point]:
    if len(points) < 2 or end_distance <= start_distance:
        return []
    result = [point_at_distance(points, start_distance)]
    travelled = 0.0
    for start, end in zip(points, points[1:]):
        segment = hypot(end[0] - start[0], end[1] - start[1])
        travelled += segment
        if start_distance < travelled < end_distance:
            result.append(end)
    result.append(point_at_distance(points, end_distance))
    return result


@dataclass(slots=True)
class CompletionFlow:
    source_id: str
    target_id: str | None
    edge_id: str | None
    frame: int = 0
    total_frames: int = 30


class GraphCanvas(tk.Canvas):
    NODE_WIDTH = 210
    NODE_HEIGHT = 104

    def __init__(
        self,
        master: tk.Misc,
        context: AppContext,
        font_family: str = "TkDefaultFont",
        on_graph_changed: Callable[[], None] | None = None,
        on_attach_file: Callable[[str], None] | None = None,
        on_copy_resource: Callable[[str], None] | None = None,
        on_agent_split: Callable[[str], None] | None = None,
        on_pet_reaction: Callable[[str | None], None] | None = None,
        on_selection_changed: Callable[[str | None, str | None], None] | None = None,
        on_focus_node_title: Callable[[str], None] | None = None,
        on_status_hint: Callable[[str], None] | None = None,
        on_create_node: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, bg=APP_BG, highlightthickness=0, **kwargs)
        self.context = context
        self.font_family = font_family
        self._type_font = tkfont.Font(family=font_family, size=9, weight="bold")
        self._title_font = tkfont.Font(family=font_family, size=12, weight="bold")
        self._meta_font = tkfont.Font(family=font_family, size=9)
        self._badge_font = tkfont.Font(family=font_family, size=8, weight="bold")
        self.on_graph_changed = on_graph_changed
        self.on_attach_file = on_attach_file
        self.on_copy_resource = on_copy_resource
        self.on_agent_split = on_agent_split
        self.on_pet_reaction = on_pet_reaction
        self.on_selection_changed = on_selection_changed
        self.on_focus_node_title = on_focus_node_title
        self.on_status_hint = on_status_hint
        self.on_create_node = on_create_node
        self._node_items: dict[str, list[int]] = {}
        self._item_to_node: dict[int, str] = {}
        self._edge_items: dict[str, list[int]] = {}
        self._item_to_edge: dict[int, str] = {}
        self._label_boxes: list[tuple[float, float, float, float]] = []
        self._selected_node_id: str | None = None
        self._selected_edge_id: str | None = None
        self._hovered_node_id: str | None = None
        self._hovered_edge_id: str | None = None
        self._drag_node_id: str | None = None
        self._drag_offset_x = 0.0
        self._drag_offset_y = 0.0
        self._pan_start_x = 0.0
        self._pan_start_y = 0.0
        self._pan_origin_x = 0.0
        self._pan_origin_y = 0.0
        self._panning = False
        self._edge_mode = False
        self._edge_start_node_id: str | None = None
        self._completion_flow: CompletionFlow | None = None
        self._completion_after_id: str | None = None
        self._reveal_active = False
        self._visible_reveal_nodes: set[str] = set()
        self._visible_reveal_edges: set[str] = set()
        self._reveal_after_id: str | None = None
        self._spotlight_node_ids: set[str] = set()
        self._spotlight_after_id: str | None = None
        self._edit_grid_mode = False
        self._dark_mode = False

        self.bind("<Button-1>", self._on_click)
        self.bind("<Shift-Button-1>", self._on_pan_start)
        self.bind("<Shift-B1-Motion>", self._on_pan_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        self.bind("<Button-4>", self._on_mouse_wheel)
        self.bind("<Button-5>", self._on_mouse_wheel)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", self._on_configure)
        self.bind("<Button-2>", self._on_context_menu)
        self.bind("<Button-3>", self._on_context_menu)
        self.bind("<Escape>", lambda _event: self.cancel_edge_mode())
        self.bind("<Delete>", self._on_delete_key)
        self.bind("<BackSpace>", self._on_delete_key)
        self.bind("<Control-0>", lambda _event: self.fit_graph_to_view())
        self.redraw()

    def set_context(self, context: AppContext) -> None:
        self.context = context
        self._selected_node_id = None
        self._selected_edge_id = None
        self._edge_mode = False
        self._edge_start_node_id = None
        self._hovered_node_id = None
        self._hovered_edge_id = None
        self._completion_flow = None
        self._reveal_active = False
        self._visible_reveal_nodes.clear()
        self._visible_reveal_edges.clear()
        self._spotlight_node_ids.clear()
        self._notify_pet_reaction(None)
        if self._completion_after_id is not None:
            self.after_cancel(self._completion_after_id)
            self._completion_after_id = None
        self._panning = False
        self.redraw()
        self._notify_selection_changed()

    def play_reveal(self, node_order: list[str] | None = None) -> None:
        if self._reveal_after_id is not None:
            self.after_cancel(self._reveal_after_id)
            self._reveal_after_id = None
        nodes = node_order or list(self.context.graph.nodes.keys())
        edges = list(self.context.graph.edges.keys())
        self._reveal_active = True
        self._visible_reveal_nodes.clear()
        self._visible_reveal_edges.clear()

        sequence: list[tuple[str, str]] = [("node", node_id) for node_id in nodes]
        sequence.extend(("edge", edge_id) for edge_id in edges)

        def step(index: int = 0) -> None:
            if index >= len(sequence):
                self._reveal_active = False
                self._reveal_after_id = None
                recommended = self._recommended_node_id()
                if recommended is not None:
                    self.spotlight_nodes([recommended], duration_ms=900)
                self.redraw()
                return
            kind, item_id = sequence[index]
            if kind == "node":
                self._visible_reveal_nodes.add(item_id)
            else:
                self._visible_reveal_edges.add(item_id)
            self.redraw()
            self._reveal_after_id = self.after(95, lambda: step(index + 1))

        step()

    def spotlight_nodes(self, node_ids: list[str], duration_ms: int = 800) -> None:
        if self._spotlight_after_id is not None:
            self.after_cancel(self._spotlight_after_id)
        self._spotlight_node_ids = set(node_ids)
        self.redraw()

        def clear() -> None:
            self._spotlight_node_ids.clear()
            self._spotlight_after_id = None
            self.redraw()

        self._spotlight_after_id = self.after(duration_ms, clear)

    def set_visual_mode(self, *, edit_grid: bool, dark_mode: bool) -> None:
        self._edit_grid_mode = edit_grid
        self._dark_mode = dark_mode
        self.configure(bg=self._canvas_bg())
        self.redraw()

    def redraw(self) -> None:
        self._redraw()

    def selected_node_id(self) -> str | None:
        return self._selected_node_id

    def selected_edge_id(self) -> str | None:
        return self._selected_edge_id

    def select_node(self, node_id: str | None) -> None:
        if node_id is not None and self.context.graph.get_node(node_id) is None:
            node_id = None
        self._selected_node_id = node_id
        if node_id is not None:
            self._selected_edge_id = None
        self.context.graph_service.set_current_node(node_id)
        self.focus_set()
        self.redraw()
        self._notify_selection_changed()

    def select_edge(self, edge_id: str | None) -> None:
        if edge_id is not None and self.context.graph.get_edge(edge_id) is None:
            edge_id = None
        self._selected_edge_id = edge_id
        if edge_id is not None:
            self._selected_node_id = None
            self.context.graph_service.set_current_node(None)
        self.focus_set()
        self.redraw()
        self._notify_selection_changed()

    def clear_selection(self) -> None:
        if self._selected_node_id is None and self._selected_edge_id is None:
            return
        self._selected_node_id = None
        self._selected_edge_id = None
        self.context.graph_service.set_current_node(None)
        self.redraw()
        self._notify_selection_changed()

    def _start_background_pan(self, event: tk.Event) -> None:
        self._panning = True
        self._drag_node_id = None
        self._pan_start_x = float(event.x)
        self._pan_start_y = float(event.y)
        self._pan_origin_x = self.context.graph.workspace.pan_x
        self._pan_origin_y = self.context.graph.workspace.pan_y

    def edit_selected_node(self) -> None:
        if self._selected_node_id is not None:
            self._edit_node(self._selected_node_id)

    def edit_node(self, node_id: str) -> None:
        self._edit_node(node_id)

    def mark_selected_node_status(self, status: NodeStatus) -> None:
        if self._selected_node_id is not None:
            self._mark_node_status(self._selected_node_id, status)

    def mark_node_status(self, node_id: str, status: NodeStatus) -> None:
        self._mark_node_status(node_id, status)

    def delete_selected_node(self) -> None:
        if self._selected_node_id is not None:
            self._delete_node(self._selected_node_id)

    def begin_edge_mode(self) -> None:
        self._edge_mode = True
        self._edge_start_node_id = None
        self._selected_edge_id = None
        self._selected_node_id = None
        self._status_hint("Choose source node")
        self.redraw()
        self._notify_selection_changed()

    def begin_edge_from_node(self, node_id: str) -> None:
        if self.context.graph.get_node(node_id) is None:
            return
        self._edge_mode = True
        self._edge_start_node_id = node_id
        self._selected_node_id = node_id
        self._selected_edge_id = None
        self._status_hint("Choose target node")
        self.redraw()
        self._notify_selection_changed()

    def cancel_edge_mode(self) -> None:
        was_active = self._edge_mode
        self._edge_mode = False
        self._edge_start_node_id = None
        if was_active:
            self._status_hint("Edge mode canceled")
        self.redraw()

    def delete_selected_edge(self) -> None:
        if self._selected_edge_id is not None:
            self._delete_edge(self._selected_edge_id)

    def edit_selected_edge(self) -> None:
        if self._selected_edge_id is not None:
            self._edit_edge(self._selected_edge_id)

    def edit_edge(self, edge_id: str) -> None:
        self._edit_edge(edge_id)

    def zoom_in(self) -> None:
        self._set_zoom(self.context.graph.workspace.zoom * 1.15)

    def zoom_out(self) -> None:
        self._set_zoom(self.context.graph.workspace.zoom / 1.15)

    def reset_view(self) -> None:
        workspace = self.context.graph.workspace
        workspace.zoom = 1.0
        workspace.pan_x = 0.0
        workspace.pan_y = 0.0
        self.redraw()

    def visible_center_graph_position(self) -> tuple[float, float]:
        self.update_idletasks()
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        center_x, center_y = self._to_graph(width / 2, height / 2)
        return (
            max(0.0, center_x - self.NODE_WIDTH / 2),
            max(0.0, center_y - self.NODE_HEIGHT / 2),
        )

    def _redraw(self) -> None:
        self.delete("all")
        self._node_items.clear()
        self._item_to_node.clear()
        self._edge_items.clear()
        self._item_to_edge.clear()
        self._label_boxes.clear()
        self._draw_mission_background()

        if not self.context.graph.nodes:
            self._draw_empty_hint()
            self._draw_edge_mode_hint()
            return

        for edge in self.context.graph.edges.values():
            if self._reveal_active and edge.id not in self._visible_reveal_edges:
                continue
            self._draw_edge(edge)
        for node in self.context.graph.nodes.values():
            if self._reveal_active and node.id not in self._visible_reveal_nodes:
                continue
            self._draw_node(node)
        self._draw_completion_overlay()
        self._draw_edge_mode_hint()

    def _draw_mission_background(self) -> None:
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        bg = self._canvas_bg()
        self.create_rectangle(0, 0, width, height, fill=bg, outline="", tags=("graph", "bg"))
        spacing = 28 if self._edit_grid_mode else 32
        grid_color = DARK_BORDER if self._dark_mode else "#CBD5E1"
        dot_color = "#27343D" if self._dark_mode else "#E2E8F0"
        if self._edit_grid_mode:
            offset_x = int(self.context.graph.workspace.pan_x) % spacing
            offset_y = int(self.context.graph.workspace.pan_y) % spacing
            for x in range(offset_x - spacing, width + spacing, spacing):
                self.create_line(x, 0, x, height, fill=grid_color, width=1, tags=("graph", "bg"))
            for y in range(offset_y - spacing, height + spacing, spacing):
                self.create_line(0, y, width, y, fill=grid_color, width=1, tags=("graph", "bg"))
        else:
            for x in range(0, width + spacing, spacing):
                for y in range(0, height + spacing, spacing):
                    self.create_oval(
                        x - 1,
                        y - 1,
                        x + 1,
                        y + 1,
                        fill=dot_color,
                        outline="",
                        tags=("graph", "bg"),
                    )
        orbit_colors = (
            ("#172554", "#1E1B4B", "#3B0A2A")
            if self._dark_mode
            else ("#EEF2FF", "#F5F3FF", "#FDF2F8")
        )
        for radius, color in zip((180, 270, 360), orbit_colors):
            self.create_oval(
                width - radius,
                -radius / 2,
                width + radius,
                radius * 1.5,
                outline=color,
                width=1,
                tags=("graph", "bg"),
            )

    def _canvas_bg(self) -> str:
        if self._dark_mode:
            return DARK_PANEL_SOFT if self._edit_grid_mode else DARK_APP_BG
        return "#EEF2F7" if self._edit_grid_mode else APP_BG

    def _surface(self) -> str:
        return DARK_SURFACE if self._dark_mode else SURFACE

    def _surface_hover(self) -> str:
        return DARK_SURFACE_HOVER if self._dark_mode else CARD_BG_HOVER

    def _text_primary(self) -> str:
        return DARK_TEXT if self._dark_mode else TEXT_PRIMARY

    def _text_muted(self) -> str:
        return DARK_MUTED if self._dark_mode else TEXT_MUTED

    def _border(self) -> str:
        return DARK_BORDER if self._dark_mode else BORDER

    def _draw_empty_hint(self) -> None:
        self.update_idletasks()
        cx = max(320, self.winfo_width() / 2)
        cy = max(220, self.winfo_height() / 2)
        card_w = 420
        card_h = 190
        x1 = cx - card_w / 2
        y1 = cy - card_h / 2
        x2 = cx + card_w / 2
        y2 = cy + card_h / 2
        self._rounded_rectangle(
            x1,
            y1,
            x2,
            y2,
            16,
            fill=self._surface(),
            outline=self._border(),
            tags=("graph", "empty-state"),
        )
        self.create_text(
            cx,
            y1 + 42,
            text="No workflow yet",
            anchor="center",
            fill=self._text_primary(),
            font=(self.font_family, 18, "bold"),
            tags=("graph", "empty-state"),
        )
        self.create_text(
            cx,
            y1 + 74,
            text="Create a node to start planning.",
            anchor="center",
            fill=self._text_muted(),
            font=(self.font_family, 11),
            tags=("graph", "empty-state"),
        )
        self._draw_empty_button(
            cx,
            y1 + 122,
            "New Node",
            "empty-new-node",
            primary=True,
        )

    def _draw_empty_button(
        self,
        cx: float,
        cy: float,
        text: str,
        tag: str,
        *,
        primary: bool,
    ) -> None:
        width = 132
        height = 34
        fill = PRIMARY if primary else self._surface()
        outline = PRIMARY if primary else self._border()
        fg = SURFACE if primary else self._text_primary()
        self._rounded_rectangle(
            cx - width / 2,
            cy - height / 2,
            cx + width / 2,
            cy + height / 2,
            8,
            fill=fill,
            outline=outline,
            tags=("graph", "empty-state", tag),
        )
        self.create_text(
            cx,
            cy,
            text=text,
            fill=fg,
            font=(self.font_family, 10, "bold" if primary else "normal"),
            tags=("graph", "empty-state", tag),
        )
        if tag == "empty-new-node" and self.on_create_node is not None:
            self.tag_bind(tag, "<Button-1>", lambda _event: self.on_create_node())
            self.tag_bind(tag, "<Enter>", lambda _event: self.configure(cursor="hand2"))
            self.tag_bind(tag, "<Leave>", lambda _event: self.configure(cursor=""))

    def _draw_edge_mode_hint(self) -> None:
        if not self._edge_mode:
            return
        message = "Choose target node" if self._edge_start_node_id else "Choose source node"
        x = self.winfo_width() / 2
        y = 26
        width = 250
        self._rounded_rectangle(
            x - width / 2,
            y - 15,
            x + width / 2,
            y + 15,
            14,
            fill=self._surface(),
            outline=self._border(),
            tags=("graph", "edge-mode-hint"),
        )
        self.create_text(
            x,
            y,
            text=f"{message}   ·   Esc to cancel",
            fill=self._text_primary(),
            font=(self.font_family, 9),
            tags=("graph", "edge-mode-hint"),
        )

    def _draw_node(self, node: Node) -> None:
        x1, y1 = self._to_screen(node.x, node.y)
        x2, y2 = self._to_screen(node.x + self.NODE_WIDTH, node.y + self.NODE_HEIGHT)
        fill, base_outline = self._node_palette(node)
        recommended_id = self._recommended_node_id()
        current_id = self.context.graph.workspace.current_node_id
        emphasized = node.id == recommended_id or node.id in self._spotlight_node_ids or (
            self.context.graph.workspace.focus_mode and node.id == current_id
        )
        selected = node.id == self._selected_node_id
        pulse = self._node_pulse_amount(node.id)
        inset = -self._scale(pulse)
        x1 += inset
        y1 += inset
        x2 -= inset
        y2 -= inset
        outline = PRIMARY if emphasized or selected else base_outline
        width = 2 if emphasized or selected else 1
        shadow = self._rounded_rectangle(
            x1 + self._scale(1),
            y1 + self._scale(3),
            x2 + self._scale(1),
            y2 + self._scale(3),
            self._scale(18),
            fill="#0B1220" if self._dark_mode else "#E2E8F0",
            outline="",
            tags=("graph", "node", f"node:{node.id}"),
        )
        if emphasized or pulse > 0:
            glow = self._rounded_rectangle(
                x1 - self._scale(3 + pulse),
                y1 - self._scale(3 + pulse),
                x2 + self._scale(3 + pulse),
                y2 + self._scale(3 + pulse),
                self._scale(22),
                fill="#064E3B" if self._dark_mode and self._is_completion_source(node.id) else "#1E3A5F" if self._dark_mode else SUCCESS_SOFT if self._is_completion_source(node.id) else PRIMARY_SOFT,
                outline="",
                tags=("graph", "node", f"node:{node.id}"),
            )
            self.tag_lower(glow, shadow)
        else:
            glow = None
        body = self._rounded_rectangle(
            x1,
            y1,
            x2,
            y2,
            self._scale(18),
            fill=("#1E3A5F" if self._dark_mode else PRIMARY_TINT) if selected or emphasized else fill,
            outline=outline,
            width=width,
            tags=("graph", "node", f"node:{node.id}"),
        )
        accent = self._node_type_accent(node.type)
        stripe = self._rounded_rectangle(
            x1,
            y1 + self._scale(12),
            x1 + self._scale(4),
            y2 - self._scale(12),
            self._scale(3),
            fill=accent,
            outline="",
            tags=("graph", "node", f"node:{node.id}"),
        )
        dot = self.create_oval(
            x1 + self._scale(14),
            y1 + self._scale(15),
            x1 + self._scale(24),
            y1 + self._scale(25),
            fill=accent,
            outline="",
            tags=("graph", "node", f"node:{node.id}"),
        )
        type_text = self.create_text(
            x1 + self._scale(32),
            y1 + self._scale(20),
            text=self._fit_text_to_width(
                node.type.value.upper(), self._type_font, self._scale(92)
            ),
            anchor="w",
            fill=self._text_muted(),
            font=self._type_font,
            tags=("graph", "node", f"node:{node.id}"),
        )
        top_meta = self.create_text(
            x2 - self._scale(14),
            y1 + self._scale(20),
            text=f"P{node.priority}  \u00b7  {node.estimated_minutes}m",
            anchor="e",
            fill=self._text_muted(),
            font=self._meta_font,
            tags=("graph", "node", f"node:{node.id}"),
        )
        title = self.create_text(
            x1 + self._scale(14),
            y1 + self._scale(50),
            text=self._fit_text_to_width(
                node.title, self._title_font, self._scale(180)
            ),
            anchor="w",
            fill=self._text_primary(),
            font=self._title_font,
            tags=("graph", "node", f"node:{node.id}"),
        )
        badge_text = self._status_text(node)
        badge_width = min(
            self._scale(86),
            self._badge_font.measure(badge_text) + self._scale(18),
        )
        badge_fill, badge_fg = self._status_palette(node.status)
        badge = self._rounded_rectangle(
            x1 + self._scale(14),
            y1 + self._scale(70),
            x1 + self._scale(14) + badge_width,
            y1 + self._scale(91),
            self._scale(10),
            fill=badge_fill,
            outline="",
            tags=("graph", "node", f"node:{node.id}"),
        )
        meta = self.create_text(
            x1 + self._scale(14) + badge_width / 2,
            y1 + self._scale(80),
            text=self._fit_text_to_width(badge_text, self._badge_font, badge_width - 8),
            anchor="center",
            fill=badge_fg,
            font=self._badge_font,
            tags=("graph", "node", f"node:{node.id}"),
        )
        items = [shadow, body, stripe, dot, type_text, top_meta, title, badge, meta]
        if node.id == recommended_id:
            next_width = self._scale(40)
            next_badge = self._rounded_rectangle(
                x2 - self._scale(14) - next_width,
                y1 + self._scale(70),
                x2 - self._scale(14),
                y1 + self._scale(91),
                self._scale(10),
                fill="#1E3A5F" if self._dark_mode else PRIMARY_SOFT,
                outline="",
                tags=("graph", "node", f"node:{node.id}"),
            )
            next_text = self.create_text(
                x2 - self._scale(14) - next_width / 2,
                y1 + self._scale(80),
                text="NEXT",
                anchor="center",
                fill=PRIMARY,
                font=self._badge_font,
                tags=("graph", "node", f"node:{node.id}"),
            )
            items.extend((next_badge, next_text))
        if glow is not None:
            items.insert(0, glow)
        self._node_items[node.id] = items
        for item in items:
            self._item_to_node[item] = node.id
        self.tag_bind(
            f"node:{node.id}",
            "<Enter>",
            lambda _event, node_id=node.id: self._set_hovered_node(node_id),
        )
        self.tag_bind(
            f"node:{node.id}",
            "<Leave>",
            lambda _event, node_id=node.id: self._clear_hovered_node(node_id),
        )

    def _draw_edge(self, edge: Edge) -> None:
        source = self.context.graph.get_node(edge.source)
        target = self.context.graph.get_node(edge.target)
        if source is None or target is None:
            return

        path = self.compute_edge_path(source, target, edge.type)
        color, dash = self._edge_style(edge)
        state = self._edge_visual_state(edge)
        if source.status == NodeStatus.DONE:
            color = SUCCESS
        if state in {"selected-path", "completion-flow"}:
            color = PRIMARY
        elif state == "hover-related":
            color = BORDER_STRONG
        elif self._hovered_node_id is not None:
            color = BORDER
        width = 2 if state != "default" else 1.2

        line = self.create_line(
            *self._flatten_points(path),
            fill=color,
            width=width,
            arrow=tk.LAST,
            dash=dash,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
            arrowshape=(8, 10, 3),
            tags=(
                "graph",
                "edge",
                f"edge:{edge.id}",
                f"edge-source:{edge.source}",
                f"edge-target:{edge.target}",
            ),
        )
        label_items = (
            self._draw_edge_label(edge, path, state)
            if self._should_show_edge_label(edge, state)
            else []
        )
        items = [line, *label_items]
        self._edge_items[edge.id] = items
        for item in items:
            self._item_to_edge[item] = edge.id
        self.tag_bind(
            f"edge:{edge.id}",
            "<Enter>",
            lambda _event, edge_id=edge.id: self._set_hovered_edge(edge_id),
        )
        self.tag_bind(
            f"edge:{edge.id}",
            "<Leave>",
            lambda _event, edge_id=edge.id: self._clear_hovered_edge(edge_id),
        )

    def _on_click(self, event: tk.Event) -> None:
        if event.state & 0x0001:
            return
        node_id = self._node_id_from_event(event)
        edge_id = self._edge_id_from_event(event)
        self._drag_node_id = None
        self._panning = False
        if self._edge_mode:
            if node_id is not None:
                self._handle_edge_mode_click(node_id)
            else:
                self._status_hint("Choose a node, or press Esc to cancel edge mode")
            return
        if node_id is not None:
            self.select_node(node_id)
            node = self.context.graph.get_node(node_id)
            if node is not None:
                graph_x, graph_y = self._event_graph_position(event)
                self._drag_node_id = node_id
                self._drag_offset_x = graph_x - node.x
                self._drag_offset_y = graph_y - node.y
            return
        if edge_id is not None:
            self.select_edge(edge_id)
            return
        self.clear_selection()
        self._start_background_pan(event)

    def _on_drag(self, event: tk.Event) -> None:
        if self._panning:
            self._on_pan_drag(event)
            return
        if self._drag_node_id is None:
            return
        graph_x, graph_y = self._event_graph_position(event)
        x = graph_x - self._drag_offset_x
        y = graph_y - self._drag_offset_y
        self.context.graph_service.move_node(
            self._drag_node_id, max(0.0, x), max(0.0, y)
        )
        self.redraw()

    def _on_release(self, _event: tk.Event) -> None:
        self._drag_node_id = None
        self._panning = False

    def _on_configure(self, _event: tk.Event) -> None:
        self.redraw()

    def _on_pan_start(self, event: tk.Event) -> None:
        self._panning = True
        self._drag_node_id = None
        self._pan_start_x = float(event.x)
        self._pan_start_y = float(event.y)
        self._pan_origin_x = self.context.graph.workspace.pan_x
        self._pan_origin_y = self.context.graph.workspace.pan_y

    def _on_pan_drag(self, event: tk.Event) -> None:
        if not self._panning:
            return
        workspace = self.context.graph.workspace
        workspace.pan_x = self._pan_origin_x + float(event.x) - self._pan_start_x
        workspace.pan_y = self._pan_origin_y + float(event.y) - self._pan_start_y
        self.redraw()

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        if getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            self.zoom_out()
        else:
            self.zoom_in()

    def _on_double_click(self, event: tk.Event) -> None:
        node_id = self._node_id_from_event(event)
        if node_id is None:
            return
        self.select_node(node_id)
        if self.on_focus_node_title is not None:
            self.on_focus_node_title(node_id)
        else:
            self._edit_node(node_id)

    def _on_motion(self, event: tk.Event) -> None:
        node_id = self._node_id_from_event(event)
        edge_id = None if node_id is not None else self._edge_id_from_event(event)
        if node_id == self._hovered_node_id and edge_id == self._hovered_edge_id:
            return
        self._hovered_node_id = node_id
        self._hovered_edge_id = edge_id
        self.redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._hovered_node_id is None and self._hovered_edge_id is None:
            return
        self._hovered_node_id = None
        self._hovered_edge_id = None
        self.redraw()

    def _set_hovered_node(self, node_id: str) -> None:
        if self._hovered_node_id != node_id:
            self._hovered_node_id = node_id
            self._hovered_edge_id = None
            self.redraw()

    def _clear_hovered_node(self, node_id: str) -> None:
        if self._hovered_node_id == node_id:
            self._hovered_node_id = None
            self.redraw()

    def _set_hovered_edge(self, edge_id: str) -> None:
        if self._hovered_edge_id != edge_id:
            self._hovered_edge_id = edge_id
            self._hovered_node_id = None
            self.redraw()

    def _clear_hovered_edge(self, edge_id: str) -> None:
        if self._hovered_edge_id == edge_id:
            self._hovered_edge_id = None
            self.redraw()

    def _on_context_menu(self, event: tk.Event) -> None:
        node_id = self._node_id_from_event(event)
        edge_id = self._edge_id_from_event(event)
        if edge_id is not None:
            self.select_edge(edge_id)
            menu = tk.Menu(self, tearoff=False)
            menu.add_command(
                label="Edit Edge", command=lambda: self._edit_edge(edge_id)
            )
            menu.add_command(
                label="Delete Edge", command=lambda: self._delete_edge(edge_id)
            )
            menu.entryconfigure("Delete Edge", foreground="#DC2626")
            menu.add_command(label="Cancel Edge Mode", command=self.cancel_edge_mode)
            menu.tk_popup(event.x_root, event.y_root)
            return
        if node_id is None:
            return
        self.select_node(node_id)
        node = self.context.graph.get_node(node_id)
        if node is None:
            return
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Open / Edit", command=lambda: self._edit_node(node_id))
        menu.add_command(
            label="Create Edge From This Node",
            command=lambda: self.begin_edge_from_node(node_id),
        )
        menu.add_separator()
        status_menu = tk.Menu(menu, tearoff=False)
        status_menu.add_command(
            label="Mark Todo",
            command=lambda: self._mark_node_status(node_id, NodeStatus.TODO),
        )
        status_menu.add_command(
            label="Mark Doing",
            command=lambda: self._mark_node_status(node_id, NodeStatus.DOING),
        )
        status_menu.add_command(
            label="Mark Done",
            command=lambda: self._mark_node_status(node_id, NodeStatus.DONE),
        )
        status_menu.add_command(
            label="Mark Blocked",
            command=lambda: self._mark_node_status(node_id, NodeStatus.BLOCKED),
        )
        status_menu.add_command(
            label="Mark Paused",
            command=lambda: self._mark_node_status(node_id, NodeStatus.PAUSED),
        )
        menu.add_cascade(label="Status", menu=status_menu)
        menu.add_separator()
        menu.add_command(
            label="Attach File",
            command=lambda: self._run_node_action(self.on_attach_file, node_id),
        )
        if node.type == NodeType.RESOURCE:
            menu.add_command(
                label="Copy Resource",
                command=lambda: self._run_node_action(self.on_copy_resource, node_id),
            )
        agent_menu = tk.Menu(menu, tearoff=False)
        agent_menu.add_command(
            label="Split Node",
            command=lambda: self._run_node_action(self.on_agent_split, node_id),
        )
        menu.add_cascade(label="Agent", menu=agent_menu)
        menu.add_separator()
        menu.add_command(
            label="Delete", command=lambda: self._delete_node(node_id)
        )
        menu.entryconfigure("Delete", foreground="#DC2626")
        menu.tk_popup(event.x_root, event.y_root)

    def _on_delete_key(self, _event: tk.Event) -> None:
        if self._selected_edge_id is not None:
            self._delete_edge(self._selected_edge_id)
            return
        self.delete_selected_node()

    def _edit_node(self, node_id: str) -> None:
        node = self.context.graph.get_node(node_id)
        if node is None:
            return
        previous_status = node.status
        dialog = NodeDialog(self, node)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.context.graph_service.update_node_detail(
                node_id,
                title=str(dialog.result["title"]),
                description=str(dialog.result["description"]),
                node_type=dialog.result["node_type"],
                status=dialog.result["status"],
                priority=int(dialog.result["priority"]),
                estimated_minutes=int(dialog.result["estimated_minutes"]),
                actual_minutes=int(dialog.result["actual_minutes"]),
                tags=dialog.result["tags"],
                resource_type=dialog.result["resource_type"],
                resource_path=str(dialog.result["resource_path"]),
                checklist=dialog.result["checklist"],
                repeat_type=dialog.result["repeat_type"],
                repeat_interval=int(dialog.result["repeat_interval"]),
                next_due_at=str(dialog.result["next_due_at"]),
                streak=int(dialog.result["streak"]),
            )
            if (
                previous_status != NodeStatus.DONE
                and dialog.result["status"] == NodeStatus.DONE
            ):
                next_node = self.context.recommendation_engine.recommend_next(
                    self.context.graph
                )
                if next_node is not None:
                    self._selected_node_id = next_node.id
                    self.context.graph_service.set_current_node(next_node.id)
                self._start_completion_flow(node_id, next_node.id if next_node else None)
            self.redraw()
            self._notify_selection_changed()
            self._notify_graph_changed()
        except PetFlowError as exc:
            messagebox.showerror("Edit node failed", str(exc), parent=self)

    def _mark_node_status(self, node_id: str, status: NodeStatus) -> None:
        try:
            self.context.graph_service.update_node_status(node_id, status)
            self._selected_node_id = node_id
            if status == NodeStatus.DONE:
                next_node = self.context.recommendation_engine.recommend_next(
                    self.context.graph
                )
                if next_node is not None:
                    self._selected_node_id = next_node.id
                    self.context.graph_service.set_current_node(next_node.id)
                self._start_completion_flow(node_id, next_node.id if next_node else None)
            self.redraw()
            self._notify_selection_changed()
            self._notify_graph_changed()
        except PetFlowError as exc:
            messagebox.showerror("Update status failed", str(exc), parent=self)

    def _delete_node(self, node_id: str) -> None:
        if not messagebox.askyesno("Delete node", "Delete this node?", parent=self):
            return
        try:
            self.context.graph_service.delete_node(node_id)
            self._selected_node_id = None
            self._selected_edge_id = None
            self.redraw()
            self._notify_selection_changed()
            self._notify_graph_changed()
        except PetFlowError as exc:
            messagebox.showerror("Delete node failed", str(exc), parent=self)

    def _delete_edge(self, edge_id: str) -> None:
        if not messagebox.askyesno("Delete edge", "Delete this edge?", parent=self):
            return
        try:
            self.context.graph_service.delete_edge(edge_id)
            self._selected_edge_id = None
            self.redraw()
            self._notify_selection_changed()
            self._notify_graph_changed()
        except PetFlowError as exc:
            messagebox.showerror("Delete edge failed", str(exc), parent=self)

    def _edit_edge(self, edge_id: str) -> None:
        edge = self.context.graph.get_edge(edge_id)
        if edge is None:
            return
        dialog = EdgeDialog(self, edge)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.context.graph_service.update_edge(
                edge_id,
                type=dialog.result["type"],
                label=str(dialog.result["label"]),
            )
            self.redraw()
            self._notify_selection_changed()
            self._notify_graph_changed()
        except PetFlowError as exc:
            messagebox.showerror("Edit edge failed", str(exc), parent=self)

    def _node_id_from_event(self, event: tk.Event) -> str | None:
        item = self.find_withtag("current")
        if not item:
            return None
        return self._item_to_node.get(item[0])

    def _edge_id_from_event(self, event: tk.Event) -> str | None:
        item = self.find_withtag("current")
        if item:
            edge_id = self._item_to_edge.get(item[0])
            if edge_id is not None:
                return edge_id
        radius = 6
        for item_id in self.find_overlapping(
            event.x - radius,
            event.y - radius,
            event.x + radius,
            event.y + radius,
        ):
            edge_id = self._item_to_edge.get(item_id)
            if edge_id is not None:
                return edge_id
        return None

    def _handle_edge_mode_click(self, node_id: str) -> None:
        if self._edge_start_node_id is None:
            self._edge_start_node_id = node_id
            self._selected_node_id = node_id
            self._selected_edge_id = None
            self._status_hint("Choose target node")
            self.redraw()
            self._notify_selection_changed()
            return
        if self._edge_start_node_id == node_id:
            self._status_hint("Choose a different target node")
            return
        try:
            edge = self.context.graph_service.create_edge(
                self._edge_start_node_id,
                node_id,
                EdgeType.DEPENDENCY,
                label="",
            )
            self._edge_mode = False
            self._edge_start_node_id = None
            self.select_edge(edge.id)
            self._status_hint("Edge created")
            self._notify_graph_changed()
        except PetFlowError as exc:
            messagebox.showerror("Create edge failed", str(exc), parent=self)

    @staticmethod
    def _run_node_action(
        action: Callable[[str], None] | None, node_id: str
    ) -> None:
        if action is not None:
            action(node_id)

    def _notify_selection_changed(self) -> None:
        if self.on_selection_changed is not None:
            self.on_selection_changed(self._selected_node_id, self._selected_edge_id)

    def _status_hint(self, message: str) -> None:
        if self.on_status_hint is not None:
            self.on_status_hint(message)

    def _notify_graph_changed(self) -> None:
        if self.on_graph_changed is not None:
            self.on_graph_changed()

    def _set_zoom(self, zoom: float) -> None:
        self.context.graph.workspace.zoom = min(2.5, max(0.4, zoom))
        self.redraw()

    def fit_graph_to_view(self, padding: float = 100.0) -> None:
        nodes = list(self.context.graph.nodes.values())
        if not nodes:
            return
        self.update_idletasks()
        viewport_width = max(1, self.winfo_width())
        viewport_height = max(1, self.winfo_height())
        min_x = min(node.x for node in nodes)
        min_y = min(node.y for node in nodes)
        max_x = max(node.x + self.NODE_WIDTH for node in nodes)
        max_y = max(node.y + self.NODE_HEIGHT for node in nodes)
        graph_width = max_x - min_x + padding * 2
        graph_height = max_y - min_y + padding * 2
        zoom = clamp(
            min(viewport_width / graph_width, viewport_height / graph_height),
            0.75,
            1.25,
        )
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        workspace = self.context.graph.workspace
        workspace.zoom = zoom
        workspace.pan_x = viewport_width / 2 - center_x * zoom
        workspace.pan_y = viewport_height / 2 - center_y * zoom
        self.configure(
            scrollregion=(
                -padding,
                -padding,
                viewport_width + padding,
                viewport_height + padding,
            )
        )
        self.redraw()

    def _event_graph_position(self, event: tk.Event) -> tuple[float, float]:
        return self._to_graph(float(event.x), float(event.y))

    def _to_screen(self, x: float, y: float) -> tuple[float, float]:
        workspace = self.context.graph.workspace
        return (
            x * workspace.zoom + workspace.pan_x,
            y * workspace.zoom + workspace.pan_y,
        )

    def _to_graph(self, x: float, y: float) -> tuple[float, float]:
        workspace = self.context.graph.workspace
        zoom = workspace.zoom or 1.0
        return (
            (x - workspace.pan_x) / zoom,
            (y - workspace.pan_y) / zoom,
        )

    def _scale(self, value: float) -> float:
        return value * self.context.graph.workspace.zoom

    def _rounded_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        **kwargs: object,
    ) -> int:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

    def compute_edge_path(
        self, source: Node, target: Node, _edge_type: EdgeType
    ) -> list[Point]:
        start = self._to_screen(
            source.x + self.NODE_WIDTH, source.y + self.NODE_HEIGHT / 2
        )
        end = self._to_screen(target.x, target.y + self.NODE_HEIGHT / 2)
        forward = target.x >= source.x - 40.0
        obstructed = self._path_intersects_other_node(source, target)
        if forward and not obstructed:
            dx = end[0] - start[0]
            offset = clamp(abs(dx) * 0.45, self._scale(60), self._scale(140))
            return sample_cubic_bezier(
                start,
                (start[0] + offset, start[1]),
                (end[0] - offset, end[1]),
                end,
            )
        return self._orthogonal_auxiliary_path(source, target, start, end)

    def _orthogonal_auxiliary_path(
        self, source: Node, target: Node, start: Point, end: Point
    ) -> list[Point]:
        lane_offset = self._scale(96)
        above = min(source.y, target.y) >= 110.0
        if above:
            lane_y = min(start[1], end[1]) - lane_offset
        else:
            lane_y = max(start[1], end[1]) + lane_offset
        exit_x = start[0] + self._scale(34)
        entry_x = end[0] - self._scale(34)
        return [
            start,
            (exit_x, start[1]),
            (exit_x, lane_y),
            (entry_x, lane_y),
            (entry_x, end[1]),
            end,
        ]

    def _path_intersects_other_node(self, source: Node, target: Node) -> bool:
        left = source.x + self.NODE_WIDTH
        right = target.x
        if right <= left:
            return False
        path_top = min(
            source.y + self.NODE_HEIGHT / 2,
            target.y + self.NODE_HEIGHT / 2,
        )
        path_bottom = max(
            source.y + self.NODE_HEIGHT / 2,
            target.y + self.NODE_HEIGHT / 2,
        )
        for node in self.context.graph.nodes.values():
            if node.id in {source.id, target.id}:
                continue
            if left < node.x + self.NODE_WIDTH and node.x < right:
                if node.y <= path_bottom and node.y + self.NODE_HEIGHT >= path_top:
                    return True
        return False

    def _draw_edge_label(
        self, edge: Edge, path: list[Point], state: str
    ) -> list[int]:
        text = self._edge_label_text(edge)
        total = path_length(path)
        center_x, center_y = point_at_distance(path, total * 0.5)
        width = self._meta_font.measure(text) + 18
        height = 22
        before_x, before_y = point_at_distance(path, max(0.0, total * 0.5 - 8))
        after_x, after_y = point_at_distance(path, min(total, total * 0.5 + 8))
        tangent_x = after_x - before_x
        tangent_y = after_y - before_y
        tangent_length = max(1.0, hypot(tangent_x, tangent_y))
        normal_x = -tangent_y / tangent_length * 12
        normal_y = tangent_x / tangent_length * 12
        candidates = [
            (center_x + normal_x, center_y + normal_y),
            (center_x - normal_x, center_y - normal_y),
            (center_x + normal_x * 2, center_y + normal_y * 2),
            (center_x - normal_x * 2, center_y - normal_y * 2),
        ]
        label_x: float | None = None
        label_y: float | None = None
        for candidate_x, candidate_y in candidates:
            box = (
                candidate_x - width / 2,
                candidate_y - height / 2,
                candidate_x + width / 2,
                candidate_y + height / 2,
            )
            if not self._label_collides(box):
                label_x, label_y = candidate_x, candidate_y
                self._label_boxes.append(box)
                break
        if label_x is None or label_y is None:
            return []
        shadow = self._rounded_rectangle(
            label_x - width / 2,
            label_y - height / 2 + 1,
            label_x + width / 2,
            label_y + height / 2 + 1,
            10,
            fill="#E5E7EB",
            outline="",
            tags=("edge", "edge-label", f"edge:{edge.id}", f"edge-label:{edge.id}"),
        )
        pill = self._rounded_rectangle(
            label_x - width / 2,
            label_y - height / 2,
            label_x + width / 2,
            label_y + height / 2,
            10,
            fill="#FFFFFF",
            outline="#E5E7EB",
            width=1,
            tags=("edge", "edge-label", f"edge:{edge.id}", f"edge-label:{edge.id}"),
        )
        label = self.create_text(
            label_x,
            label_y,
            text=text,
            fill="#64748B",
            font=(self.font_family, 9),
            tags=("edge", "edge-label", f"edge:{edge.id}", f"edge-label:{edge.id}"),
        )
        return [shadow, pill, label]

    def _label_collides(self, box: tuple[float, float, float, float]) -> bool:
        for existing in self._label_boxes:
            if self._boxes_overlap(box, existing):
                return True
        for node in self.context.graph.nodes.values():
            x1, y1 = self._to_screen(node.x, node.y)
            x2, y2 = self._to_screen(
                node.x + self.NODE_WIDTH, node.y + self.NODE_HEIGHT
            )
            if self._boxes_overlap(box, (x1 - 5, y1 - 5, x2 + 5, y2 + 5)):
                return True
        return False

    @staticmethod
    def _boxes_overlap(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        return not (
            first[2] < second[0]
            or first[0] > second[2]
            or first[3] < second[1]
            or first[1] > second[3]
        )

    def _edge_visual_state(self, edge: Edge) -> str:
        if self._completion_flow is not None and edge.id == self._completion_flow.edge_id:
            return "completion-flow"
        if (
            edge.id == self._selected_edge_id
            or edge.id in self._recommended_edge_ids()
        ):
            return "selected-path"
        if (
            edge.id == self._hovered_edge_id
            or self._hovered_node_id in {edge.source, edge.target}
        ):
            return "hover-related"
        return "default"

    def _should_show_edge_label(self, edge: Edge, state: str) -> bool:
        return state != "default" or edge.id == self._hovered_edge_id

    @staticmethod
    def _flatten_points(points: list[Point]) -> list[float]:
        coordinates: list[float] = []
        for x, y in points:
            coordinates.extend((x, y))
        return coordinates

    def _recommended_node_id(self) -> str | None:
        node = self.context.recommendation_engine.recommend_next(self.context.graph)
        return node.id if node is not None else None

    def _recommended_edge_ids(self) -> set[str]:
        recommended_id = self._recommended_node_id()
        if recommended_id is None:
            return set()
        return {
            edge.id
            for edge in self.context.graph.edges.values()
            if (
                edge.target == recommended_id
                and edge.type == EdgeType.DEPENDENCY
            )
            or (
                edge.source == recommended_id
                and edge.type in {EdgeType.DEPENDENCY, EdgeType.RECOMMENDATION}
            )
        }

    def _start_completion_flow(self, source_id: str, target_id: str | None) -> None:
        edge_id = self._outgoing_edge_id(source_id, target_id)
        self._completion_flow = CompletionFlow(source_id, target_id, edge_id)
        if self._completion_after_id is not None:
            self.after_cancel(self._completion_after_id)
        self._notify_pet_reaction("complete")
        self._advance_completion_flow()

    def _advance_completion_flow(self) -> None:
        if self._completion_flow is None:
            return
        if self._completion_flow.frame <= 5:
            self._notify_pet_reaction("complete")
        elif self._completion_flow.frame < 25:
            self._notify_pet_reaction("move")
        else:
            self._notify_pet_reaction("arrive")
        self.redraw()
        self._completion_flow.frame += 1
        if self._completion_flow.frame > self._completion_flow.total_frames:
            self._completion_flow = None
            self._completion_after_id = None
            self._notify_pet_reaction(None)
            self.redraw()
            return
        self._completion_after_id = self.after(40, self._advance_completion_flow)

    def _draw_completion_overlay(self) -> None:
        flow = self._completion_flow
        if flow is None or flow.edge_id is None or flow.frame < 5:
            return
        edge = self.context.graph.get_edge(flow.edge_id)
        if edge is None:
            return
        source = self.context.graph.get_node(edge.source)
        target = self.context.graph.get_node(edge.target)
        if source is None or target is None:
            return
        path = self.compute_edge_path(source, target, edge.type)
        total = path_length(path)
        progress = min(1.0, (flow.frame - 5) / 19)
        end_distance = total * progress
        segment = extract_subpath(path, max(0.0, end_distance - 84), end_distance)
        if len(segment) >= 2:
            self.create_line(
                *self._flatten_points(segment),
                fill="#3B82F6",
                width=3,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                tags=("edge-flow-animation",),
            )

    def _outgoing_edge_id(self, source_id: str, target_id: str | None) -> str | None:
        if target_id is None or target_id == source_id:
            return None
        for edge in self.context.graph.edges.values():
            if edge.source == source_id and edge.target == target_id:
                return edge.id
        return None

    def _node_pulse_amount(self, node_id: str) -> float:
        flow = self._completion_flow
        if flow is None:
            return 0.0
        if node_id == flow.source_id and flow.frame <= 5:
            relative = flow.frame / 4
            return 3.0 * max(0.0, 1.0 - abs(relative * 2 - 1.0))
        if node_id == flow.target_id and flow.frame >= 25:
            relative = (flow.frame - 25) / 5
            return 3.0 * max(0.0, 1.0 - abs(relative * 2 - 1.0))
        return 0.0

    def _is_completion_source(self, node_id: str) -> bool:
        return self._completion_flow is not None and self._completion_flow.source_id == node_id

    def _notify_pet_reaction(self, reaction: str | None) -> None:
        if self.on_pet_reaction is not None:
            self.on_pet_reaction(reaction)

    @staticmethod
    def _edge_style(edge: Edge) -> tuple[str, tuple[int, ...] | None]:
        if edge.type == EdgeType.DEPENDENCY:
            return BORDER_STRONG, None
        if edge.type == EdgeType.ROUTINE:
            return BORDER_STRONG, (8, 8)
        if edge.type == EdgeType.RECOMMENDATION:
            return BORDER_STRONG, (8, 8)
        if edge.type == EdgeType.TRIGGER:
            return BORDER_STRONG, (8, 8)
        return BORDER_STRONG, None

    @staticmethod
    def _fit_text(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "..."

    @staticmethod
    def _fit_text_to_width(text: str, font: tkfont.Font, max_width: float) -> str:
        if font.measure(text) <= max_width:
            return text
        suffix = "..."
        fitted = text
        while fitted and font.measure(fitted + suffix) > max_width:
            fitted = fitted[:-1]
        return fitted + suffix if fitted else suffix

    @classmethod
    def _edge_label_text(cls, edge: Edge) -> str:
        if edge.label:
            return cls._fit_text(edge.label, 28)
        return edge.type.value

    def _node_palette(self, node: Node) -> tuple[str, str]:
        if node.status == NodeStatus.BLOCKED:
            return self._surface(), WARNING
        return self._surface(), self._border()

    @staticmethod
    def _node_type_accent(node_type: NodeType) -> str:
        if node_type == NodeType.RESOURCE:
            return SUCCESS
        if node_type == NodeType.REWARD:
            return PINK
        if node_type == NodeType.CHECKPOINT:
            return PURPLE
        if node_type == NodeType.ROUTINE:
            return WARNING
        return PRIMARY

    def _status_text(self, node: Node) -> str:
        parts = [node.status.value.capitalize()]
        if node.type == NodeType.ROUTINE:
            state = self._routine_state_label(node)
            if state:
                parts.append(state.capitalize())
        return " / ".join(parts)

    @staticmethod
    def _status_palette(status: NodeStatus) -> tuple[str, str]:
        if status == NodeStatus.DONE:
            return SUCCESS_SOFT, SUCCESS
        if status == NodeStatus.DOING:
            return PRIMARY_SOFT, PRIMARY
        if status == NodeStatus.BLOCKED:
            return DANGER_SOFT, DANGER
        if status == NodeStatus.PAUSED:
            return CARD_BG_HOVER, TEXT_MUTED
        return CARD_BG_HOVER, TEXT_SECONDARY

    def _routine_state_label(self, node: Node) -> str:
        state = self.context.routine_service.routine_state(node)
        if state == "overdue":
            return "overdue"
        if state == "due":
            return "due"
        if state == "scheduled":
            return "scheduled"
        return ""
