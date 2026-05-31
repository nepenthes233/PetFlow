from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
import tkinter as tk
from tkinter import messagebox

from petflow.app.app_context import AppContext
from petflow.domain.entities import Edge, Node
from petflow.domain.enums import EdgeType, NodeStatus, NodeType, RepeatType, ResourceType
from petflow.domain.exceptions import PetFlowError


class InspectorPanel(tk.Frame):
    """Modern side-panel editor for the selected node or edge.

    The panel intentionally edits through GraphService instead of touching the
    graph model directly. Dialogs can still exist as an advanced/fallback path,
    but the main editing flow should stay here.
    """

    BG = "#FFFFFF"
    CARD = "#F8FAFC"
    CARD_2 = "#F1F5F9"
    TEXT = "#111827"
    MUTED = "#64748B"
    BORDER = "#E5E7EB"
    ACCENT = "#2563EB"
    ACCENT_SOFT = "#DBEAFE"
    DANGER = "#DC2626"
    DANGER_SOFT = "#FEE2E2"

    def __init__(
        self,
        master: tk.Misc,
        context: AppContext,
        font_family: str,
        on_changed: Callable[[], None] | None = None,
        on_status_change: Callable[[str, NodeStatus], None] | None = None,
        on_delete_node: Callable[[str], None] | None = None,
        on_delete_edge: Callable[[str], None] | None = None,
        on_advanced_node: Callable[[str], None] | None = None,
        on_advanced_edge: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, width=330, bg=self.BG, highlightthickness=0, takefocus=0)
        self.pack_propagate(False)
        self.context = context
        self.font_family = font_family
        self.on_changed = on_changed
        self.on_status_change = on_status_change
        self.on_delete_node = on_delete_node
        self.on_delete_edge = on_delete_edge
        self.on_advanced_node = on_advanced_node
        self.on_advanced_edge = on_advanced_edge
        self._node_id: str | None = None
        self._edge_id: str | None = None
        self._title_entry: tk.Entry | None = None
        self._title_var = tk.StringVar(value="")
        self._description_text: tk.Text | None = None
        self._label_var = tk.StringVar(value="")
        self._estimated_var = tk.StringVar(value="")
        self._actual_var = tk.StringVar(value="")
        self._tags_var = tk.StringVar(value="")
        self._resource_path_var = tk.StringVar(value="")
        self._repeat_interval_var = tk.StringVar(value="")
        self._next_due_var = tk.StringVar(value="")
        self._save_feedback_var = tk.StringVar(value="")
        self._syncing = False
        self._active_scroll_canvas: tk.Canvas | None = None
        self._last_scroll_fraction = 0.0
        self.show_empty()

    def set_context(self, context: AppContext) -> None:
        self.context = context
        self._node_id = None
        self._edge_id = None
        self.show_empty()

    def show_selection(
        self, node_id: str | None = None, edge_id: str | None = None
    ) -> None:
        self._node_id = node_id
        self._edge_id = None if node_id is not None else edge_id
        self.refresh(preserve_scroll=False)

    def refresh(self, preserve_scroll: bool = True) -> None:
        self._last_scroll_fraction = self._current_scroll_fraction() if preserve_scroll else 0.0
        if self._node_id is not None:
            node = self.context.graph.get_node(self._node_id)
            if node is not None:
                self._draw_node(node)
                return
        if self._edge_id is not None:
            edge = self.context.graph.get_edge(self._edge_id)
            if edge is not None:
                self._draw_edge(edge)
                return
        self.show_empty()

    def focus_title(self) -> None:
        if self._title_entry is None:
            return
        self._title_entry.focus_set()
        self._title_entry.select_range(0, tk.END)

    def show_empty(self) -> None:
        self._clear()
        shell = tk.Frame(self, bg=self.BG, padx=18, pady=20)
        shell.pack(fill="both", expand=True)
        tk.Label(
            shell,
            text="EDIT",
            bg=self.BG,
            fg=self.ACCENT,
            font=(self.font_family, 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            shell,
            text="Select something",
            bg=self.BG,
            fg=self.TEXT,
            font=(self.font_family, 18, "bold"),
        ).pack(anchor="w", pady=(2, 8))
        tk.Label(
            shell,
            text=(
                "Click a node or edge to edit it here.\n"
                "Use New Node for instant creation, or New Edge to connect nodes."
            ),
            bg=self.BG,
            fg=self.MUTED,
            justify="left",
            wraplength=280,
            font=(self.font_family, 10),
        ).pack(anchor="w", pady=(0, 18))
        self._hint_card(shell, "Tip", "Double-click a node to jump to its title field.")

    def _draw_node(self, node: Node) -> None:
        self._clear()
        self._syncing = True
        self._title_var.set(node.title)
        self._estimated_var.set(str(node.estimated_minutes))
        self._actual_var.set(str(node.actual_minutes))
        self._tags_var.set(", ".join(node.tags))
        self._resource_path_var.set(node.resource_path)
        self._repeat_interval_var.set(str(node.repeat_interval))
        self._next_due_var.set(node.next_due_at[:10] if node.next_due_at else "")
        self._save_feedback_var.set("")
        self._syncing = False

        outer = tk.Frame(self, bg=self.BG)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=self.BG, highlightthickness=0, borderwidth=0, width=330, takefocus=0)
        scrollbar = tk.Scrollbar(
            outer,
            orient="vertical",
            command=canvas.yview,
            width=8,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        body = tk.Frame(canvas, bg=self.BG, padx=18, pady=18)
        window_id = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        body.bind(
            "<Configure>",
            lambda _event=None: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event=None: canvas.itemconfigure(
                window_id, width=canvas.winfo_width() if event is None else event.width
            ),
        )
        self._active_scroll_canvas = canvas

        self._eyebrow(body, "EDIT NODE")
        self._title_entry = self._entry(body, self._title_var, size=17, bold=True)
        self._title_entry.pack(fill="x", pady=(4, 14))
        self._title_entry.bind("<Return>", lambda _event: self._apply_node_text("title"))
        self._title_entry.bind("<FocusOut>", lambda _event: self._apply_node_text("title"))

        top_actions = tk.Frame(body, bg=self.BG)
        top_actions.pack(fill="x", pady=(0, 8))
        self._soft_button(
            top_actions,
            "Save Node",
            command=lambda: self._save_node_form(node.id),
            primary=True,
        ).pack(side="left")
        self._soft_button(
            top_actions,
            "Delete Node",
            command=lambda: self._call_node_action(self.on_delete_node, node.id),
            danger=True,
        ).pack(side="right")
        tk.Label(
            body,
            textvariable=self._save_feedback_var,
            bg=self.BG,
            fg=self.MUTED,
            font=(self.font_family, 9),
        ).pack(anchor="w", pady=(0, 4))

        self._section(body, "Type")
        self._segmented(
            body,
            [(item.value.title(), item, item == node.type) for item in NodeType],
            lambda value: self._update_node(node.id, type=value),
            columns=2,
        )

        self._section(body, "Status")
        self._segmented(
            body,
            [(item.value.title(), item, item == node.status) for item in NodeStatus],
            lambda value: self._change_status(node.id, value),
            columns=2,
        )

        self._section(body, "Priority")
        self._segmented(
            body,
            [(str(value), value, value == node.priority) for value in range(1, 6)],
            lambda value: self._update_node(node.id, priority=value),
            columns=5,
        )

        self._section(body, "Estimate")
        self._segmented(
            body,
            [
                ("15m", 15, node.estimated_minutes == 15),
                ("30m", 30, node.estimated_minutes == 30),
                ("60m", 60, node.estimated_minutes == 60),
                ("120m", 120, node.estimated_minutes == 120),
            ],
            lambda value: self._update_node(node.id, estimated_minutes=value),
            columns=4,
        )
        row = tk.Frame(body, bg=self.BG)
        row.pack(fill="x", pady=(8, 0))
        self._small_label(row, "Custom minutes").pack(side="left")
        custom = self._entry(row, self._estimated_var, width=8)
        custom.pack(side="right")
        custom.bind(
            "<Return>", lambda _event: self._apply_int(node.id, "estimated_minutes", self._estimated_var)
        )
        custom.bind(
            "<FocusOut>", lambda _event: self._apply_int(node.id, "estimated_minutes", self._estimated_var)
        )

        self._section(body, "Actual Time")
        actual = self._entry(body, self._actual_var)
        actual.pack(fill="x")
        actual.bind("<Return>", lambda _event: self._apply_int(node.id, "actual_minutes", self._actual_var))
        actual.bind("<FocusOut>", lambda _event: self._apply_int(node.id, "actual_minutes", self._actual_var))

        self._section(body, "Due")
        self._segmented(
            body,
            [
                ("Today", "today", False),
                ("Tomorrow", "tomorrow", False),
                ("+7 Days", "week", False),
                ("Clear", "clear", node.next_due_at is None),
            ],
            lambda value: self._set_due(node.id, value),
            columns=4,
        )
        due = self._entry(body, self._next_due_var)
        due.pack(fill="x", pady=(8, 0))
        due.bind("<Return>", lambda _event: self._apply_due(node.id))
        due.bind("<FocusOut>", lambda _event: self._apply_due(node.id))

        self._section(body, "Repeat")
        self._segmented(
            body,
            [(item.value.title(), item, item == node.repeat_type) for item in RepeatType],
            lambda value: self._update_node(node.id, repeat_type=value),
            columns=2,
        )
        row = tk.Frame(body, bg=self.BG)
        row.pack(fill="x", pady=(8, 0))
        self._small_label(row, "Repeat interval").pack(side="left")
        interval = self._entry(row, self._repeat_interval_var, width=8)
        interval.pack(side="right")
        interval.bind(
            "<Return>", lambda _event: self._apply_int(node.id, "repeat_interval", self._repeat_interval_var, minimum=1)
        )
        interval.bind(
            "<FocusOut>", lambda _event: self._apply_int(node.id, "repeat_interval", self._repeat_interval_var, minimum=1)
        )

        self._section(body, "Description")
        self._description_text = tk.Text(
            body,
            height=5,
            wrap="word",
            bg=self.CARD,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            highlightcolor=self.BORDER,
            takefocus=1,
            padx=10,
            pady=8,
            font=(self.font_family, 10),
        )
        self._description_text.insert("1.0", node.description)
        self._description_text.pack(fill="x")
        self._description_text.bind("<FocusOut>", lambda _event: self._apply_description(node.id))
        self._description_text.bind("<Control-Return>", lambda _event: self._apply_description(node.id))

        self._section(body, "Tags")
        tags = self._entry(body, self._tags_var)
        tags.pack(fill="x")
        tags.bind("<Return>", lambda _event: self._apply_tags(node.id))
        tags.bind("<FocusOut>", lambda _event: self._apply_tags(node.id))

        self._section(body, "Resource")
        self._segmented(
            body,
            [(item.value.title(), item, item == node.resource_type) for item in ResourceType],
            lambda value: self._update_node(node.id, resource_type=value),
            columns=2,
        )
        path = self._entry(body, self._resource_path_var)
        path.pack(fill="x", pady=(8, 0))
        path.bind("<Return>", lambda _event: self._apply_node_text("resource_path"))
        path.bind("<FocusOut>", lambda _event: self._apply_node_text("resource_path"))

        self._section(body, "More")
        actions = tk.Frame(body, bg=self.BG)
        actions.pack(fill="x", pady=(0, 20))
        self._soft_button(
            actions,
            "Advanced...",
            command=lambda: self._call_node_action(self.on_advanced_node, node.id),
        ).pack(side="left")

        self._bind_scroll_to_descendants(outer, canvas)
        self._restore_scroll_position(canvas)

    def _draw_edge(self, edge: Edge) -> None:
        self._clear()
        source = self.context.graph.get_node(edge.source)
        target = self.context.graph.get_node(edge.target)
        self._syncing = True
        self._label_var.set(edge.label)
        self._syncing = False

        body = tk.Frame(self, bg=self.BG, padx=18, pady=18)
        body.pack(fill="both", expand=True)
        self._eyebrow(body, "EDIT EDGE")
        tk.Label(
            body,
            text=f"{source.title if source else edge.source}  →  {target.title if target else edge.target}",
            bg=self.BG,
            fg=self.TEXT,
            justify="left",
            wraplength=280,
            font=(self.font_family, 16, "bold"),
        ).pack(anchor="w", pady=(4, 12))

        self._section(body, "Type")
        self._segmented(
            body,
            [(item.value.title(), item, item == edge.type) for item in EdgeType],
            lambda value: self._update_edge(edge.id, type=value),
            columns=2,
        )

        self._section(body, "Label")
        label = self._entry(body, self._label_var)
        label.pack(fill="x")
        label.bind("<Return>", lambda _event: self._apply_edge_label(edge.id))
        label.bind("<FocusOut>", lambda _event: self._apply_edge_label(edge.id))

        self._hint_card(
            body,
            "Edge flow",
            "Dependency edges block the target until source tasks are done. Routine and recommendation edges may form loops.",
        )

        actions = tk.Frame(body, bg=self.BG)
        actions.pack(fill="x", pady=(8, 0))
        self._soft_button(
            actions,
            "Advanced...",
            command=lambda: self._call_edge_action(self.on_advanced_edge, edge.id),
        ).pack(side="left")
        self._soft_button(
            actions,
            "Delete Edge",
            command=lambda: self._call_edge_action(self.on_delete_edge, edge.id),
            danger=True,
        ).pack(side="right")

    def _clear(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._active_scroll_canvas = None
        self._title_entry = None
        self._description_text = None

    def _current_scroll_fraction(self) -> float:
        canvas = self._active_scroll_canvas
        if canvas is None:
            return self._last_scroll_fraction
        try:
            return float(canvas.yview()[0])
        except tk.TclError:
            return self._last_scroll_fraction

    def _restore_scroll_position(self, canvas: tk.Canvas) -> None:
        fraction = max(0.0, min(1.0, self._last_scroll_fraction))
        canvas.after_idle(lambda: self._safe_yview_moveto(canvas, fraction))

    def _safe_yview_moveto(self, canvas: tk.Canvas, fraction: float) -> None:
        try:
            canvas.yview_moveto(fraction)
        except tk.TclError:
            return

    def _bind_scroll_to_descendants(self, root: tk.Misc, canvas: tk.Canvas) -> None:
        def bind_widget(widget: tk.Misc) -> None:
            try:
                widget.bind(
                    "<MouseWheel>",
                    lambda event=None, target=canvas: self._scroll_target(target, event),
                )
                widget.bind(
                    "<Button-4>",
                    lambda event=None, target=canvas: self._scroll_target(target, event),
                )
                widget.bind(
                    "<Button-5>",
                    lambda event=None, target=canvas: self._scroll_target(target, event),
                )
            except tk.TclError:
                return
            for child in widget.winfo_children():
                bind_widget(child)

        bind_widget(root)

    def _scroll_target(self, canvas: tk.Canvas, event: tk.Event | None) -> str:
        if event is None:
            return "break"
        try:
            self._active_scroll_canvas = canvas
            number = getattr(event, "num", None)
            if number == 4:
                self._scroll_canvas_pixels(canvas, -48.0)
            elif number == 5:
                self._scroll_canvas_pixels(canvas, 48.0)
            else:
                delta = getattr(event, "delta", 0)
                if delta == 0:
                    return "break"
                if abs(delta) >= 120:
                    pixels = -float(delta) / 120.0 * 48.0
                else:
                    pixels = -float(delta) * 3.0
                self._scroll_canvas_pixels(canvas, pixels)
            self._last_scroll_fraction = float(canvas.yview()[0])
        except tk.TclError:
            pass
        return "break"

    def _scroll_canvas_pixels(self, canvas: tk.Canvas, pixels: float) -> None:
        bbox = canvas.bbox("all")
        if bbox is None:
            return
        content_height = max(1.0, float(bbox[3] - bbox[1]))
        viewport_height = max(1.0, float(canvas.winfo_height()))
        scrollable_height = max(0.0, content_height - viewport_height)
        if scrollable_height <= 0:
            return
        top_fraction = float(canvas.yview()[0])
        top_pixel = top_fraction * scrollable_height
        target_pixel = max(0.0, min(scrollable_height, top_pixel + pixels))
        canvas.yview_moveto(target_pixel / scrollable_height)

    def _eyebrow(self, master: tk.Misc, text: str) -> None:
        tk.Label(
            master,
            text=text,
            bg=self.BG,
            fg=self.ACCENT,
            font=(self.font_family, 9, "bold"),
        ).pack(anchor="w")

    def _section(self, master: tk.Misc, text: str) -> None:
        tk.Label(
            master,
            text=text,
            bg=self.BG,
            fg=self.TEXT,
            font=(self.font_family, 10, "bold"),
        ).pack(anchor="w", pady=(16, 7))

    def _small_label(self, master: tk.Misc, text: str) -> tk.Label:
        return tk.Label(
            master,
            text=text,
            bg=self.BG,
            fg=self.MUTED,
            font=(self.font_family, 9),
        )

    def _entry(
        self,
        master: tk.Misc,
        variable: tk.StringVar,
        width: int | None = None,
        size: int = 10,
        bold: bool = False,
    ) -> tk.Entry:
        return tk.Entry(
            master,
            textvariable=variable,
            width=width or 1,
            bg=self.CARD,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            highlightcolor=self.BORDER,
            takefocus=1,
            font=(self.font_family, size, "bold" if bold else "normal"),
        )

    def _segmented(
        self,
        master: tk.Misc,
        options: list[tuple[str, object, bool]],
        command: Callable[[object], None],
        columns: int = 2,
    ) -> None:
        grid = tk.Frame(master, bg=self.BG)
        grid.pack(fill="x")
        buttons: list[tuple[tk.Button, object, str]] = []

        def paint(selected_value: object) -> None:
            for button, value, label in buttons:
                selected = value == selected_value
                button.configure(
                    bg=self.ACCENT_SOFT if selected else self.CARD,
                    fg=self.ACCENT if selected else self.TEXT,
                    font=(self.font_family, 9, "bold" if selected else "normal"),
                )

        def choose(choice: object) -> None:
            command(choice)
            paint(choice)

        initial_value: object | None = None
        for index, (label, value, selected) in enumerate(options):
            if selected:
                initial_value = value
            button = tk.Button(
                grid,
                text=label,
                command=lambda choice=value: choose(choice),
                bg=self.ACCENT_SOFT if selected else self.CARD,
                fg=self.ACCENT if selected else self.TEXT,
                activebackground=self.ACCENT_SOFT,
                activeforeground=self.ACCENT,
                relief="flat",
                borderwidth=0,
                highlightthickness=0,
                takefocus=0,
                padx=8,
                pady=7,
                cursor="hand2",
                font=(self.font_family, 9, "bold" if selected else "normal"),
            )
            buttons.append((button, value, label))
            row = index // columns
            col = index % columns
            button.grid(row=row, column=col, sticky="ew", padx=(0, 6), pady=(0, 6))
        for col in range(columns):
            grid.columnconfigure(col, weight=1)
        if initial_value is not None:
            paint(initial_value)

    def _soft_button(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        danger: bool = False,
        primary: bool = False,
    ) -> tk.Button:
        bg = self.ACCENT if primary else self.DANGER_SOFT if danger else self.CARD_2
        fg = "#FFFFFF" if primary else self.DANGER if danger else self.TEXT
        active_bg = self.ACCENT if primary else self.DANGER_SOFT if danger else self.CARD
        active_fg = "#FFFFFF" if primary else self.DANGER if danger else self.TEXT
        return tk.Button(
            master,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=active_fg,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            takefocus=0,
            padx=12,
            pady=8,
            cursor="hand2",
            font=(self.font_family, 9, "bold" if danger or primary else "normal"),
        )

    def _hint_card(self, master: tk.Misc, title: str, text: str) -> None:
        card = tk.Frame(master, bg=self.CARD, padx=12, pady=10)
        card.pack(fill="x", pady=(10, 14))
        tk.Label(
            card,
            text=title,
            bg=self.CARD,
            fg=self.TEXT,
            font=(self.font_family, 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card,
            text=text,
            bg=self.CARD,
            fg=self.MUTED,
            justify="left",
            wraplength=250,
            font=(self.font_family, 9),
        ).pack(anchor="w", pady=(3, 0))

    def _change_status(self, node_id: str, status: object) -> None:
        if not isinstance(status, NodeStatus):
            return
        if self.on_status_change is not None:
            self.on_status_change(node_id, status)
            return
        self._update_node_status(node_id, status)

    def _update_node_status(self, node_id: str, status: NodeStatus) -> None:
        try:
            self.context.graph_service.update_node_status(node_id, status)
            self._after_update()
        except PetFlowError as exc:
            messagebox.showerror("Update status failed", str(exc), parent=self)
            self.refresh(preserve_scroll=True)

    def _update_node(self, node_id: str, **changes: object) -> None:
        try:
            self.context.graph_service.update_node(node_id, **changes)
            self._after_update()
        except PetFlowError as exc:
            messagebox.showerror("Update node failed", str(exc), parent=self)
            self.refresh(preserve_scroll=True)

    def _update_edge(self, edge_id: str, **changes: object) -> None:
        try:
            self.context.graph_service.update_edge(edge_id, **changes)
            self._after_update()
        except PetFlowError as exc:
            messagebox.showerror("Update edge failed", str(exc), parent=self)
            self.refresh(preserve_scroll=True)

    def _apply_node_text(self, field: str) -> None:
        if self._syncing or self._node_id is None:
            return
        if field == "title":
            value = self._title_var.get().strip()
        elif field == "resource_path":
            value = self._resource_path_var.get().strip()
        else:
            return
        node = self.context.graph.get_node(self._node_id)
        if node is None or getattr(node, field) == value:
            return
        self._update_node(self._node_id, **{field: value})

    def _apply_description(self, node_id: str) -> None:
        if self._syncing or self._description_text is None:
            return
        value = self._description_text.get("1.0", "end-1c").strip()
        node = self.context.graph.get_node(node_id)
        if node is not None and node.description != value:
            self._update_node(node_id, description=value)

    def _apply_tags(self, node_id: str) -> None:
        if self._syncing:
            return
        node = self.context.graph.get_node(node_id)
        tags = [part.strip() for part in self._tags_var.get().split(",") if part.strip()]
        if node is not None and node.tags != tags:
            self._update_node(node_id, tags=tags)

    def _apply_int(
        self,
        node_id: str,
        field: str,
        variable: tk.StringVar,
        minimum: int = 0,
    ) -> None:
        if self._syncing:
            return
        try:
            value = int(variable.get().strip() or "0")
        except ValueError:
            messagebox.showerror("Invalid number", "Please enter a whole number.", parent=self)
            self.refresh(preserve_scroll=True)
            return
        value = max(minimum, value)
        node = self.context.graph.get_node(node_id)
        if node is not None and getattr(node, field) != value:
            self._update_node(node_id, **{field: value})

    def _set_due(self, node_id: str, value: object) -> None:
        today = date.today()
        if value == "today":
            due = today.isoformat()
        elif value == "tomorrow":
            due = (today + timedelta(days=1)).isoformat()
        elif value == "week":
            due = (today + timedelta(days=7)).isoformat()
        elif value == "clear":
            due = None
        else:
            return
        self._next_due_var.set(due or "")
        self._update_node(node_id, next_due_at=due)

    def _apply_due(self, node_id: str) -> None:
        if self._syncing:
            return
        value = self._next_due_var.get().strip() or None
        node = self.context.graph.get_node(node_id)
        if node is not None and node.next_due_at != value:
            self._update_node(node_id, next_due_at=value)

    def _save_node_form(self, node_id: str) -> None:
        if self._syncing:
            return
        node = self.context.graph.get_node(node_id)
        if node is None:
            self.refresh(preserve_scroll=True)
            return

        try:
            estimated_minutes = int(self._estimated_var.get().strip() or "0")
            actual_minutes = int(self._actual_var.get().strip() or "0")
            repeat_interval = int(self._repeat_interval_var.get().strip() or "1")
        except ValueError:
            messagebox.showerror(
                "Invalid number",
                "Please enter whole numbers for time and repeat interval.",
                parent=self,
            )
            self.refresh(preserve_scroll=True)
            return

        description = ""
        if self._description_text is not None:
            description = self._description_text.get("1.0", "end-1c").strip()
        tags = [part.strip() for part in self._tags_var.get().split(",") if part.strip()]

        try:
            self.context.graph_service.update_node_detail(
                node_id,
                title=self._title_var.get().strip(),
                description=description,
                node_type=node.type,
                status=node.status,
                priority=node.priority,
                estimated_minutes=estimated_minutes,
                actual_minutes=actual_minutes,
                tags=tags,
                resource_type=node.resource_type,
                resource_path=self._resource_path_var.get().strip(),
                checklist=node.checklist,
                repeat_type=node.repeat_type,
                repeat_interval=repeat_interval,
                next_due_at=self._next_due_var.get().strip(),
                streak=node.streak,
            )
        except PetFlowError as exc:
            messagebox.showerror("Save node failed", str(exc), parent=self)
            self.refresh(preserve_scroll=True)
            return

        self._save_feedback_var.set("Saved")
        self.after(1800, self._clear_save_feedback)
        self._after_update()

    def _clear_save_feedback(self) -> None:
        self._save_feedback_var.set("")

    def _apply_edge_label(self, edge_id: str) -> None:
        if self._syncing:
            return
        value = self._label_var.get().strip()
        edge = self.context.graph.get_edge(edge_id)
        if edge is not None and edge.label != value:
            self._update_edge(edge_id, label=value)

    def _call_node_action(
        self, action: Callable[[str], None] | None, node_id: str
    ) -> None:
        if action is not None:
            action(node_id)

    def _call_edge_action(
        self, action: Callable[[str], None] | None, edge_id: str
    ) -> None:
        if action is not None:
            action(edge_id)

    def _after_update(self) -> None:
        # Do not rebuild the whole Inspector for routine edits. Rebuilding the
        # panel causes a visible flash and resets the exact scroll/content state.
        # The underlying graph is already updated; controls update themselves
        # locally, while the canvas/recommendation view refreshes via callback.
        if self.on_changed is not None:
            self.on_changed()
