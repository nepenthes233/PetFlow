from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import json
from queue import Empty, Queue
from pathlib import Path
import random
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

from petflow.agent.agent_client import AgentClient
from petflow.agent.agent_executor import AgentExecutor
from petflow.agent.prompts import PromptBuilder
from petflow.app.app_context import AppContext
from petflow.config import (
    ASSETS_DIR,
    DEFAULT_GRAPH_PATH,
    SAVE_GRAPH_DIR,
    SESSION_STATE_PATH,
    AppConfig,
)
from petflow.domain.enums import NodeStatus, NodeType, PetStateType
from petflow.domain.exceptions import PetFlowError
from petflow.system.clipboard_watcher import ClipboardWatcher
from petflow.system.focus_monitor import FocusMonitor
from petflow.ui.agent_dialog import AgentDialog
from petflow.ui.agenda_panel import AgendaPanel, SavedGraphTasks
from petflow.ui.inspector_panel import InspectorPanel
from petflow.ui.graph_canvas import GraphCanvas
from petflow.ui.icon_button import IconButton
from petflow.ui.fonts import apply_ui_font_defaults
from petflow.ui.pet_assistant_panel import PetAssistantPanel
from petflow.ui.settings_dialog import SettingsDialog
from petflow.ui.theme import (
    COLOR_BORDER,
    COLOR_MUTED,
    COLOR_PANEL,
    COLOR_PRIMARY,
    COLOR_TEXT,
    DARK_APP_BG,
    DARK_BORDER,
    DARK_BORDER_STRONG,
    DARK_MUTED,
    DARK_PANEL,
    DARK_PANEL_SOFT,
    DARK_PRIMARY,
    DARK_PRIMARY_SOFT,
    DARK_SURFACE,
    DARK_TEXT,
    DARK_TEXT_SECONDARY,
)


class MainWindow:
    def __init__(self) -> None:
        self.config = AppConfig()
        self.context = AppContext.create()
        self.current_graph_path: Path | None = self._initial_graph_path()
        try:
            self.graph = self.context.storage_service.load_graph(
                self.current_graph_path
            )
        except PetFlowError:
            self.current_graph_path = DEFAULT_GRAPH_PATH
            self.graph = self.context.storage_service.load_graph(DEFAULT_GRAPH_PATH)
        self.context = AppContext.create(self.graph)
        self.clipboard_watcher = ClipboardWatcher()
        self.focus_monitor = FocusMonitor()
        self.focus_started_at: datetime | None = None
        self.status_message = "Ready"
        self.status_after_id: str | None = None
        self.agenda_panel: AgendaPanel | None = None
        self.pet_panel: PetAssistantPanel | None = None
        self.inspector_panel: InspectorPanel | None = None
        self.right_panel: tk.Frame | None = None
        self.right_body: tk.Frame | None = None
        self.edit_tab_button: tk.Button | None = None
        self.companion_tab_button: tk.Button | None = None
        self.edit_mode_button: IconButton | None = None
        self.agenda_toggle_button: IconButton | None = None
        self.right_toggle_button: IconButton | None = None
        self.focus_mode_button: IconButton | None = None
        self.theme_mode_button: IconButton | None = None
        self.focus_chip: tk.Frame | None = None
        self.focus_chip_icon: tk.Label | None = None
        self.focus_time_label: tk.Label | None = None
        self.focus_title_label: tk.Label | None = None
        self.focus_time_var: tk.StringVar
        self.focus_title_var: tk.StringVar
        self.logo_image: ImageTk.PhotoImage | None = None
        self.workspace_panes: tk.PanedWindow | None = None
        self._agenda_visible = True
        self._pet_panel_visible = True
        self._edit_mode = False
        self._dark_mode = self.context.graph.workspace.theme == "dark"
        self._right_tab = "companion"
        self._pet_agent_busy = False
        self._pet_agent_results: Queue[
            tuple[str, dict[str, object] | None, PetFlowError | None]
        ] = Queue()

        self.root = tk.Tk()
        self.focus_time_var = tk.StringVar(value="00:00")
        self.focus_title_var = tk.StringVar(value="Choose a task to focus")
        self.ui_font_family = apply_ui_font_defaults(self.root)
        self.root.title(self.config.app_name)
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.root.minsize(self.config.min_width, self.config.min_height)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    def _build_ui(self) -> None:
        self.root.configure(bg="#F6F8FB")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        toolbar = tk.Frame(
            self.root,
            width=self.config.window_width,
            height=64,
            bg="#FFFFFF",
            highlightthickness=1,
            highlightbackground="#E5E7EB",
        )
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_propagate(False)

        left = tk.Frame(toolbar, bg="#FFFFFF")
        left.pack(side="left", padx=(18, 0), pady=12)
        self.logo_image = self._load_logo()
        if self.logo_image is not None:
            tk.Label(left, image=self.logo_image, bg="#FFFFFF").pack(
                side="left", padx=(0, 8)
            )
        tk.Label(
            left,
            text="PetFlow",
            bg="#FFFFFF",
            fg="#111827",
            font=(self.ui_font_family, 18, "bold"),
        ).pack(side="left", padx=(0, 18))

        tools = tk.Frame(toolbar, bg="#FFFFFF")
        tools.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=12)

        self._icon_button(tools, "node-add", "New node", self.create_node, primary=True).pack(
            side="left", padx=(0, 4)
        )
        self._icon_button(tools, "edge-add", "New edge", self.begin_edge_mode).pack(
            side="left", padx=(0, 4)
        )
        self._icon_button(tools, "complete", "Complete selected checkpoint", self.mark_selected_done).pack(
            side="left", padx=(0, 4)
        )
        self.edit_mode_button = self._icon_button(
            tools, "edit", "Edit mode", self.toggle_edit_mode
        )
        self.edit_mode_button.pack(side="left", padx=(0, 10))

        self._separator(tools).pack(side="left", fill="y", padx=(0, 10), pady=5)
        for icon, tooltip, command in (
            ("save", "Save graph", self.save_graph),
            ("load", "Load graph", self.load_graph),
            ("recommend", "Recommend next task", self.recommend_next),
        ):
            self._icon_button(tools, icon, tooltip, command).pack(side="left", padx=(0, 4))

        self._separator(tools).pack(side="left", fill="y", padx=(6, 10), pady=5)
        for icon, tooltip, command in (
            ("arrange", "Arrange nodes", self.layout_graph),
            ("fit", "Fit view (Ctrl+0)", self.fit_view),
            ("reset", "Reset view", self.reset_view),
        ):
            self._icon_button(tools, icon, tooltip, command).pack(side="left", padx=(0, 4))

        self._separator(tools).pack(side="left", fill="y", padx=(6, 10), pady=5)
        self.agenda_toggle_button = self._icon_button(
            tools, "agenda", "Hide schedule panel", self.toggle_agenda_panel, selected=True
        )
        self.agenda_toggle_button.pack(side="left", padx=(0, 4))
        self.right_toggle_button = self._icon_button(
            tools, "right-panel", "Hide right panel", self.toggle_pet_panel, selected=True
        )
        self.right_toggle_button.pack(side="left", padx=(0, 10))

        for icon, tooltip, command in (
            ("clipboard", "Capture clipboard", self.capture_clipboard),
            ("review", "Review graph", self.show_review),
            ("settings", "Settings and API key", self.open_settings_dialog),
        ):
            self._icon_button(tools, icon, tooltip, command).pack(side="left", padx=(0, 4))

        self.focus_mode_var = tk.BooleanVar(
            value=self.context.graph.workspace.focus_mode
        )
        right = tk.Frame(toolbar, bg="#FFFFFF")
        right.pack(side="right", padx=(0, 18), pady=12)
        self.focus_mode_button = self._icon_button(
            right,
            "focus",
            "Start focus mode",
            self.toggle_focus_mode,
            selected=self.context.graph.workspace.focus_mode,
        )
        self.focus_mode_button.pack(side="left")
        self.theme_mode_button = self._icon_button(
            right,
            "theme",
            "Switch to light mode" if self._dark_mode else "Switch to dark mode",
            self.toggle_theme_mode,
            selected=self._dark_mode,
        )
        self.theme_mode_button.pack(side="left", padx=(6, 0))

        banner = tk.Frame(
            self.root,
            bg="#EFF6FF",
            highlightthickness=1,
            highlightbackground="#DBEAFE",
            padx=20,
            pady=10,
        )
        banner.grid(row=1, column=0, sticky="ew")
        banner.columnconfigure(0, weight=1)
        self.recommendation_var = tk.StringVar(value="Suggested next checkpoint: No checkpoint available")
        self.recommendation_detail_var = tk.StringVar(value="Create a node to begin.")
        tk.Label(
            banner,
            textvariable=self.recommendation_var,
            bg="#EFF6FF",
            fg="#111827",
            anchor="w",
            justify="left",
            font=(self.ui_font_family, 11, "bold"),
        ).grid(row=0, column=0, sticky="ew")
        tk.Label(
            banner,
            textvariable=self.recommendation_detail_var,
            bg="#EFF6FF",
            fg="#6B7280",
            anchor="w",
            justify="left",
            font=(self.ui_font_family, 9),
        ).grid(row=1, column=0, sticky="ew", pady=(3, 0))
        self.focus_chip = tk.Frame(
            banner,
            bg=COLOR_PANEL,
            padx=12,
            pady=8,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
        )
        focus_head = tk.Frame(self.focus_chip, bg=COLOR_PANEL)
        focus_head.pack(anchor="w", fill="x")
        self.focus_chip_icon = tk.Label(
            focus_head,
            text="●",
            bg=COLOR_PANEL,
            fg=COLOR_PRIMARY,
            font=(self.ui_font_family, 10, "bold"),
        )
        self.focus_chip_icon.pack(side="left", padx=(0, 6))
        tk.Label(
            focus_head,
            text="Focus",
            bg=COLOR_PANEL,
            fg=COLOR_PRIMARY,
            font=(self.ui_font_family, 9, "bold"),
        ).pack(side="left")
        self.focus_time_label = tk.Label(
            self.focus_chip,
            textvariable=self.focus_time_var,
            bg=COLOR_PANEL,
            fg=COLOR_TEXT,
            font=(self.ui_font_family, 18, "bold"),
        )
        self.focus_time_label.pack(anchor="w", pady=(2, 0))
        self.focus_title_label = tk.Label(
            self.focus_chip,
            textvariable=self.focus_title_var,
            bg=COLOR_PANEL,
            fg=COLOR_MUTED,
            font=(self.ui_font_family, 9, "bold"),
        )
        self.focus_title_label.pack(anchor="w")
        self._refresh_focus_chip()

        workspace = tk.Frame(self.root, bg="#F6F8FB")
        workspace.grid(row=2, column=0, sticky="nsew")
        workspace.columnconfigure(0, weight=1)
        workspace.rowconfigure(0, weight=1)
        self.workspace_panes = tk.PanedWindow(
            workspace,
            orient="horizontal",
            bg="#E5E7EB",
            bd=0,
            sashwidth=6,
            sashrelief="flat",
            showhandle=False,
            opaqueresize=True,
        )
        self.workspace_panes.grid(row=0, column=0, sticky="nsew")
        self.workspace_panes.bind(
            "<ButtonRelease-1>", lambda _event: self.root.after_idle(self.fit_view)
        )

        self.agenda_panel = AgendaPanel(
            self.workspace_panes,
            self.context.agenda_service,
            self._select_agenda_node,
            self.ui_font_family,
            self.toggle_agenda_panel,
        )

        self.canvas = GraphCanvas(
            self.workspace_panes,
            self.context,
            font_family=self.ui_font_family,
            on_graph_changed=self._on_canvas_graph_changed,
            on_attach_file=self.attach_file_to_selected_node,
            on_copy_resource=self.copy_selected_resource,
            on_agent_split=self.open_agent_dialog,
            on_pet_reaction=self._render_pet,
            on_selection_changed=self._on_canvas_selection_changed,
            on_focus_node_title=self._focus_inspector_title,
            on_status_hint=self._set_status,
            on_create_node=self.create_node,
        )

        self._build_right_panel()
        self._rebuild_workspace_panes()

        self.agenda_panel.refresh(
            self.context.graph,
            saved_graphs=self._saved_graph_task_groups(),
        )
        self._update_recommendation_label()
        self._render_pet()
        self.root.bind("<Control-0>", lambda _event: self.fit_view())
        self.root.after_idle(self.fit_view)

        self.status_var = tk.StringVar(value=self.status_message)
        tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            padx=14,
            pady=6,
            bg="#FFFFFF",
            fg="#6B7280",
            font=(self.ui_font_family, 9),
            highlightthickness=1,
            highlightbackground="#E5E7EB",
        ).grid(row=3, column=0, sticky="ew")
        self._style_panel_buttons()
        self._style_focus_button()
        self._apply_theme()
        self._refresh_status_bar()

    def _load_logo(self) -> ImageTk.PhotoImage | None:
        path = ASSETS_DIR / "brand" / "petflow_logo.png"
        if not path.exists():
            return None
        try:
            image = Image.open(path).convert("RGBA").resize((30, 30))
            return ImageTk.PhotoImage(image)
        except OSError:
            return None

    def _icon_button(
        self,
        master: tk.Misc,
        icon: str,
        tooltip: str,
        command: Callable[[], None],
        primary: bool = False,
        selected: bool = False,
    ) -> IconButton:
        return IconButton(
            master,
            icon,
            tooltip,
            command=command,
            primary=primary,
            selected=selected,
        )

    def _separator(self, master: tk.Misc) -> tk.Frame:
        return tk.Frame(master, width=1, bg="#E5E7EB")

    def _build_right_panel(self) -> None:
        if self.workspace_panes is None:
            return
        self.right_panel = tk.Frame(
            self.workspace_panes,
            width=340,
            bg="#FFFFFF",
            highlightthickness=1,
            highlightbackground="#E5E7EB",
            highlightcolor="#E5E7EB",
            takefocus=0,
        )
        self.right_panel.pack_propagate(False)
        tabs = tk.Frame(self.right_panel, bg="#FFFFFF", padx=12, pady=12)
        tabs.pack(fill="x")
        self.edit_tab_button = tk.Button(
            tabs,
            text="Edit",
            command=lambda: self._show_right_tab("edit"),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            takefocus=0,
            padx=14,
            pady=8,
            cursor="hand2",
            font=(self.ui_font_family, 9, "bold"),
        )
        self.edit_tab_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.companion_tab_button = tk.Button(
            tabs,
            text="Companion",
            command=lambda: self._show_right_tab("companion"),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            takefocus=0,
            padx=14,
            pady=8,
            cursor="hand2",
            font=(self.ui_font_family, 9, "bold"),
        )
        self.companion_tab_button.pack(side="left", fill="x", expand=True)

        self.right_body = tk.Frame(self.right_panel, bg="#FFFFFF")
        self.right_body.pack(fill="both", expand=True)

        self.inspector_panel = InspectorPanel(
            self.right_body,
            self.context,
            self.ui_font_family,
            on_changed=self._on_inspector_graph_changed,
            on_status_change=self._change_node_status_from_inspector,
            on_delete_node=self._delete_node_from_inspector,
            on_delete_edge=self._delete_edge_from_inspector,
            on_advanced_node=self._advanced_edit_node,
            on_advanced_edge=self._advanced_edit_edge,
        )
        self.pet_panel = PetAssistantPanel(
            self.right_body,
            self.ui_font_family,
            self._submit_pet_request,
            self.toggle_pet_panel,
        )
        self._show_right_tab("companion")

    def _show_right_tab(self, tab: str) -> None:
        self._right_tab = tab
        if self.inspector_panel is None or self.pet_panel is None:
            return
        self.inspector_panel.pack_forget()
        self.pet_panel.pack_forget()
        if tab == "companion":
            self.pet_panel.pack(fill="both", expand=True)
        else:
            self.inspector_panel.pack(fill="both", expand=True)
        self._style_right_tabs()

    def _style_right_tabs(self) -> None:
        for name, button in (
            ("edit", self.edit_tab_button),
            ("companion", self.companion_tab_button),
        ):
            if button is None:
                continue
            selected = name == self._right_tab
            selected_bg = "#1E3A5F" if self._dark_mode else "#DBEAFE"
            idle_bg = "#111B21" if self._dark_mode else "#F8FAFC"
            hover_bg = "#1F2C34" if self._dark_mode else "#F1F5F9"
            selected_fg = "#93C5FD" if self._dark_mode else "#2563EB"
            idle_fg = "#8696A0" if self._dark_mode else "#64748B"
            active_fg = "#E9EDEF" if self._dark_mode else "#111827"
            button.configure(
                bg=selected_bg if selected else idle_bg,
                fg=selected_fg if selected else idle_fg,
                activebackground=selected_bg if selected else hover_bg,
                activeforeground=selected_fg if selected else active_fg,
            )

    def toggle_edit_mode(self) -> None:
        self._edit_mode = not self._edit_mode
        if self._edit_mode:
            self._ensure_right_panel_visible()
            self._show_right_tab("edit")
            self._set_status("Edit mode: on")
            if self.inspector_panel is not None:
                self.inspector_panel.show_selection(
                    self.canvas.selected_node_id(), self.canvas.selected_edge_id()
                )
        else:
            self.canvas.cancel_edge_mode()
            if self._pet_panel_visible:
                self._show_right_tab("companion")
            self._set_status("Edit mode: off")
        self._style_edit_mode_button()

    def _set_edit_mode(self, enabled: bool) -> None:
        if self._edit_mode == enabled:
            if enabled:
                self._ensure_right_panel_visible()
                self._show_right_tab("edit")
            return
        self._edit_mode = enabled
        if enabled:
            self._ensure_right_panel_visible()
            self._show_right_tab("edit")
        elif self._pet_panel_visible:
            self._show_right_tab("companion")
        self._style_edit_mode_button()

    def _style_edit_mode_button(self) -> None:
        if self.edit_mode_button is None:
            return
        active = self._edit_mode
        self.edit_mode_button.set_selected(active)
        self.edit_mode_button.set_tooltip(
            "Leave edit mode" if active else "Edit mode"
        )
        self.canvas.set_visual_mode(edit_grid=active, dark_mode=self._dark_mode)

    def _style_panel_buttons(self) -> None:
        if self.agenda_toggle_button is not None:
            self.agenda_toggle_button.set_selected(self._agenda_visible)
            self.agenda_toggle_button.set_tooltip(
                "Hide schedule panel" if self._agenda_visible else "Show schedule panel"
            )
        if self.right_toggle_button is not None:
            self.right_toggle_button.set_selected(self._pet_panel_visible)
            self.right_toggle_button.set_tooltip(
                "Hide right panel" if self._pet_panel_visible else "Show right panel"
            )

    def _style_focus_button(self) -> None:
        if self.focus_mode_button is None:
            return
        enabled = bool(self.context.graph.workspace.focus_mode)
        self.focus_mode_button.set_selected(enabled)
        self.focus_mode_button.set_tooltip(
            "Stop focus mode" if enabled else "Start focus mode"
        )

    def toggle_theme_mode(self) -> None:
        self._dark_mode = not self._dark_mode
        self.context.graph.workspace.theme = "dark" if self._dark_mode else "light"
        self._apply_theme()

    def _apply_theme(self) -> None:
        bg = DARK_APP_BG if self._dark_mode else "#F6F8FB"
        panel = DARK_PANEL if self._dark_mode else "#FFFFFF"
        soft = DARK_PANEL_SOFT if self._dark_mode else "#EFF6FF"
        border = DARK_BORDER if self._dark_mode else "#E5E7EB"
        text = DARK_TEXT if self._dark_mode else "#111827"
        muted = DARK_MUTED if self._dark_mode else "#6B7280"
        self.root.configure(bg=bg)
        self._apply_ttk_theme(panel=panel, soft=soft, border=border, text=text, muted=muted)
        self._apply_widget_theme(self.root, panel=panel, soft=soft, border=border, text=text, muted=muted)
        if self.theme_mode_button is not None:
            self.theme_mode_button.set_selected(self._dark_mode)
            self.theme_mode_button.set_tooltip(
                "Switch to light mode" if self._dark_mode else "Switch to dark mode"
            )
        self._style_right_tabs()
        self._style_panel_buttons()
        self._style_focus_button()
        self.canvas.set_visual_mode(edit_grid=self._edit_mode, dark_mode=self._dark_mode)

    def _apply_ttk_theme(
        self,
        *,
        panel: str,
        soft: str,
        border: str,
        text: str,
        muted: str,
    ) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=panel, foreground=text, fieldbackground=soft)
        style.configure("TFrame", background=panel, bordercolor=border)
        style.configure("TLabel", background=panel, foreground=text)
        style.configure(
            "TEntry",
            fieldbackground=soft,
            foreground=text,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            insertcolor=text,
        )
        style.configure(
            "TCombobox",
            fieldbackground=soft,
            background=soft,
            foreground=text,
            arrowcolor=muted,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
        )
        style.configure(
            "TSpinbox",
            fieldbackground=soft,
            background=soft,
            foreground=text,
            arrowcolor=muted,
            bordercolor=border,
        )
        style.configure(
            "TButton",
            background=soft,
            foreground=text,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            focusthickness=0,
        )
        style.map(
            "TButton",
            background=[("active", DARK_BORDER if self._dark_mode else "#F1F5F9")],
            foreground=[("active", text)],
        )
        style.configure("TLabelframe", background=panel, bordercolor=border)
        style.configure("TLabelframe.Label", background=panel, foreground=muted)
        style.configure("TCheckbutton", background=panel, foreground=text)

    def _apply_widget_theme(
        self,
        widget: tk.Misc,
        *,
        panel: str,
        soft: str,
        border: str,
        text: str,
        muted: str,
    ) -> None:
        cls = widget.winfo_class()
        try:
            if isinstance(widget, IconButton):
                widget.set_dark_mode(self._dark_mode)
            elif cls in {"Frame", "TFrame"}:
                widget.configure(bg=panel)
            elif cls == "Label":
                fg = str(widget.cget("fg")).lower()
                widget.configure(
                    bg=panel,
                    fg=muted if fg in {"#6b7280", "#64748b", "#94a3b8", "#475569", "#8696a0"} else text,
                )
            elif cls == "Button":
                widget.configure(
                    bg=soft,
                    fg=text,
                    activebackground=DARK_BORDER if self._dark_mode else "#F1F5F9",
                    activeforeground=text,
                    highlightbackground=border,
                    highlightcolor=border,
                )
            elif cls in {"Text", "Entry", "Spinbox", "Listbox"}:
                widget.configure(
                    bg=soft,
                    fg=text,
                    insertbackground=text,
                    highlightbackground=border,
                    highlightcolor=border,
                    selectbackground=DARK_PRIMARY_SOFT if self._dark_mode else "#DBEAFE",
                    selectforeground=text,
                )
            elif cls in {"Checkbutton", "Radiobutton"}:
                widget.configure(
                    bg=panel,
                    fg=text,
                    activebackground=panel,
                    activeforeground=text,
                    selectcolor=soft,
                    highlightbackground=border,
                )
            elif cls == "Scrollbar":
                widget.configure(
                    bg=soft,
                    activebackground=DARK_BORDER_STRONG if self._dark_mode else "#CBD5E1",
                    troughcolor=panel,
                    highlightbackground=border,
                )
            elif cls == "Panedwindow":
                widget.configure(bg=border)
            elif cls == "Canvas" and widget is not self.canvas:
                widget.configure(bg=panel, highlightbackground=border)
            for option, value in (
                ("background", panel),
                ("highlightbackground", border),
                ("highlightcolor", border),
            ):
                try:
                    widget.configure(**{option: value})
                except tk.TclError:
                    pass
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._apply_widget_theme(child, panel=panel, soft=soft, border=border, text=text, muted=muted)

    def _ensure_right_panel_visible(self) -> None:
        if not self._pet_panel_visible:
            self._pet_panel_visible = True
            self._rebuild_workspace_panes()
            self._style_panel_buttons()

    def toggle_agenda_panel(self) -> None:
        self._agenda_visible = not self._agenda_visible
        self._rebuild_workspace_panes()
        self._style_panel_buttons()

    def toggle_pet_panel(self) -> None:
        self._pet_panel_visible = not self._pet_panel_visible
        self._rebuild_workspace_panes()
        if self._pet_panel_visible:
            if self._edit_mode:
                self._show_right_tab("edit")
            else:
                self._show_right_tab("companion")
        self._style_panel_buttons()

    def _rebuild_workspace_panes(self) -> None:
        if (
            self.workspace_panes is None
            or self.agenda_panel is None
            or self.right_panel is None
        ):
            return
        for pane in self.workspace_panes.panes():
            self.workspace_panes.forget(pane)
        if self._agenda_visible:
            self.workspace_panes.add(
                self.agenda_panel, width=280, minsize=110, stretch="never"
            )
        self.workspace_panes.add(self.canvas, minsize=360, stretch="always")
        if self._pet_panel_visible:
            self.workspace_panes.add(
                self.right_panel, width=340, minsize=230, stretch="never"
            )
        self.root.after_idle(self.fit_view)

    def create_node(self) -> None:
        try:
            try:
                x, y = self.canvas.visible_center_graph_position()
            except tk.TclError:
                x, y = self._next_node_position(NodeType.TASK)
            node = self.context.graph_service.create_node(
                title="Untitled Task",
                node_type=NodeType.TASK,
                status=NodeStatus.TODO,
                priority=3,
                estimated_minutes=30,
                x=x,
                y=y,
            )
            self._set_edit_mode(True)
            self.canvas.select_node(node.id)
            self.canvas.redraw()
            self.canvas.spotlight_nodes([node.id])
            self._refresh_agenda()
            self._update_recommendation_label()
            if self.inspector_panel is not None:
                self.inspector_panel.show_selection(node.id, None)
                self.root.after(80, self.inspector_panel.focus_title)
            self._set_status("Node created — rename it in the Edit panel")
        except PetFlowError as exc:
            messagebox.showerror("Create node failed", str(exc), parent=self.root)

    def edit_selected_node(self) -> None:
        self.canvas.edit_selected_node()

    def mark_selected_done(self) -> None:
        self.canvas.mark_selected_node_status(NodeStatus.DONE)
        self._update_recommendation_label()
        self.canvas.redraw()
        self._set_status("Node marked done")

    def delete_selected_node(self) -> None:
        self.canvas.delete_selected_node()

    def begin_edge_mode(self) -> None:
        self._set_edit_mode(True)
        self.canvas.begin_edge_mode()

    def delete_selected_edge(self) -> None:
        self.canvas.delete_selected_edge()

    def edit_selected_edge(self) -> None:
        self.canvas.edit_selected_edge()

    def _initial_graph_path(self) -> Path:
        session_path = self._session_graph_path()
        if session_path is not None:
            return session_path
        saved_files = self._graph_slot_files()
        if saved_files:
            return random.choice(saved_files)
        return DEFAULT_GRAPH_PATH

    def _session_graph_path(self) -> Path | None:
        if not SESSION_STATE_PATH.exists():
            return None
        try:
            data = json.loads(SESSION_STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        slot_name = str(data.get("current_slot", "")).strip()
        if not slot_name:
            return None
        path = SAVE_GRAPH_DIR / Path(slot_name).name
        if path.exists():
            return path
        return None

    def _graph_slot_files(self) -> list[Path]:
        SAVE_GRAPH_DIR.mkdir(parents=True, exist_ok=True)
        return sorted(SAVE_GRAPH_DIR.glob("*.json"), key=lambda path: path.name.lower())

    def _graph_slot_path(self, name: str) -> Path:
        slot_name = Path(name.strip()).name
        if not slot_name:
            raise PetFlowError("Save slot name cannot be empty.")
        if Path(slot_name).suffix.lower() != ".json":
            slot_name = f"{slot_name}.json"
        return SAVE_GRAPH_DIR / slot_name

    def _current_graph_slot_name(self) -> str | None:
        if self.current_graph_path is None:
            return None
        try:
            current_path = self.current_graph_path.resolve()
            save_dir = SAVE_GRAPH_DIR.resolve()
        except OSError:
            return None
        if current_path.parent != save_dir or not current_path.exists():
            return None
        return current_path.name

    def _ask_graph_slot_path(self, mode: str) -> Path | None:
        SAVE_GRAPH_DIR.mkdir(parents=True, exist_ok=True)
        files = self._graph_slot_files()
        is_save = mode == "save"
        current_slot_name = self._current_graph_slot_name()
        title = "Save Graph Slot" if is_save else "Load Graph Slot"
        action_label = "Save" if is_save else "Load"
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg="#FFFFFF")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.geometry("360x420")
        result: dict[str, Path | None] = {"path": None}

        body = tk.Frame(dialog, bg="#FFFFFF", padx=18, pady=18)
        body.pack(fill="both", expand=True)
        tk.Label(
            body,
            text=title,
            bg="#FFFFFF",
            fg="#111827",
            font=(self.ui_font_family, 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            body,
            text="Choose an existing column or type a new one.",
            bg="#FFFFFF",
            fg="#64748B",
            font=(self.ui_font_family, 9),
        ).pack(anchor="w", pady=(4, 12))

        name_var = tk.StringVar(
            value=(
                current_slot_name
                or (files[0].name if files else DEFAULT_GRAPH_PATH.name)
            )
        )
        listbox = tk.Listbox(
            body,
            height=10,
            bg="#F8FAFC",
            fg="#111827",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#E5E7EB",
            selectbackground="#DBEAFE",
            selectforeground="#111827",
            font=(self.ui_font_family, 10),
        )
        listbox.pack(fill="both", expand=True)

        def refresh_slot_list(selected_name: str | None = None) -> None:
            nonlocal files
            files = self._graph_slot_files()
            listbox.delete(0, tk.END)
            for path in files:
                listbox.insert(tk.END, path.name)
            if not files:
                name_var.set(DEFAULT_GRAPH_PATH.name)
                return
            names = [path.name for path in files]
            index = names.index(selected_name) if selected_name in names else 0
            listbox.selection_set(index)
            listbox.see(index)
            name_var.set(names[index])

        refresh_slot_list(current_slot_name or (files[0].name if files else None))

        def sync_selection(_event: tk.Event | None = None) -> None:
            selection = listbox.curselection()
            if selection:
                name_var.set(str(listbox.get(selection[0])))

        listbox.bind("<<ListboxSelect>>", sync_selection)
        listbox.bind("<Double-Button-1>", lambda _event: confirm())

        tk.Label(
            body,
            text="Column name",
            bg="#FFFFFF",
            fg="#64748B",
            font=(self.ui_font_family, 9, "bold"),
        ).pack(anchor="w", pady=(12, 4))
        name_entry = tk.Entry(
            body,
            textvariable=name_var,
            bg="#F8FAFC",
            fg="#111827",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#E5E7EB",
            insertbackground="#111827",
            font=(self.ui_font_family, 10),
        )
        name_entry.pack(fill="x", ipady=6)
        name_entry.bind("<Return>", lambda _event: confirm())
        if is_save:
            name_entry.focus_set()

        actions = tk.Frame(body, bg="#FFFFFF")
        actions.pack(fill="x", pady=(16, 0))

        def cancel() -> None:
            dialog.destroy()

        def confirm() -> None:
            try:
                path = self._graph_slot_path(name_var.get())
            except PetFlowError as exc:
                messagebox.showerror(title, str(exc), parent=dialog)
                return
            if not is_save and not path.exists():
                messagebox.showinfo(
                    title,
                    "Choose an existing saved column.",
                    parent=dialog,
                )
                return
            result["path"] = path
            dialog.destroy()

        def delete_selected_slot() -> None:
            try:
                path = self._graph_slot_path(name_var.get())
            except PetFlowError as exc:
                messagebox.showerror(title, str(exc), parent=dialog)
                return
            if not path.exists():
                messagebox.showinfo(
                    title,
                    "Choose an existing saved column to delete.",
                    parent=dialog,
                )
                return
            confirmed = messagebox.askyesno(
                "Delete saved graph",
                f"Delete saved graph '{path.name}'?",
                parent=dialog,
            )
            if not confirmed:
                return
            try:
                path.unlink()
            except OSError as exc:
                messagebox.showerror(
                    "Delete failed",
                    f"Could not delete {path.name}: {exc}",
                    parent=dialog,
                )
                return
            if self.current_graph_path == path:
                self.current_graph_path = None
            refresh_slot_list()
            self._refresh_agenda()

        tk.Button(
            actions,
            text="Delete",
            command=delete_selected_slot,
            relief="flat",
            padx=12,
            pady=7,
            bg="#FEE2E2",
            fg="#B91C1C",
            activebackground="#FECACA",
            activeforeground="#991B1B",
        ).pack(side="left")
        tk.Button(
            actions,
            text="Cancel",
            command=cancel,
            relief="flat",
            padx=12,
            pady=7,
        ).pack(side="right", padx=(8, 0))
        tk.Button(
            actions,
            text=action_label,
            command=confirm,
            relief="flat",
            padx=14,
            pady=7,
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
        ).pack(side="right")

        self.root.wait_window(dialog)
        return result["path"]

    def save_graph(self) -> None:
        path = self._ask_graph_slot_path("save")
        if path is None:
            return
        try:
            self.context.storage_service.save_graph(self.context.graph, path)
            self.current_graph_path = path
            self._set_status(f"Saved: {Path(path).name}")
            self._refresh_agenda()
        except PetFlowError as exc:
            messagebox.showerror("Save failed", str(exc), parent=self.root)

    def load_graph(self) -> None:
        path = self._ask_graph_slot_path("load")
        if path is None:
            return
        try:
            graph = self.context.storage_service.load_graph(path)
            self.current_graph_path = path
            self.context = AppContext.create(graph)
            self._dark_mode = self.context.graph.workspace.theme == "dark"
            if self.inspector_panel is not None:
                self.inspector_panel.set_context(self.context)
            self.canvas.set_context(self.context)
            self._refresh_agenda(preserve_scroll=False)
            self.focus_mode_var.set(self.context.graph.workspace.focus_mode)
            self.focus_started_at = (
                datetime.now() if self.context.graph.workspace.focus_mode else None
            )
            self._style_focus_button()
            self._apply_theme()
            self._refresh_focus_chip()
            self._update_recommendation_label()
            self._sync_pet_to_recommendation()
            self._set_status(f"Loaded: {Path(path).name}")
            self.root.after_idle(self.fit_view)
        except PetFlowError as exc:
            messagebox.showerror("Load failed", str(exc), parent=self.root)

    def layout_graph(self) -> None:
        self.context.graph_layout_service.apply_grid_layout(self.context.graph_service)
        self.canvas.redraw()
        self._refresh_agenda()
        self._set_status("Graph layout refreshed")
        self.root.after_idle(self.fit_view)

    def zoom_in(self) -> None:
        self.canvas.zoom_in()
        self._set_status(f"Zoom: {self.context.graph.workspace.zoom:.0%}")

    def zoom_out(self) -> None:
        self.canvas.zoom_out()
        self._set_status(f"Zoom: {self.context.graph.workspace.zoom:.0%}")

    def reset_view(self) -> None:
        self.canvas.reset_view()
        self._set_status("View reset")

    def fit_view(self) -> None:
        self.canvas.fit_graph_to_view()
        self._set_status("View fitted")

    def recommend_next(self) -> None:
        node = self.context.recommendation_engine.recommend_next(self.context.graph)
        if node is None:
            self.recommendation_var.set("Suggested next checkpoint: No checkpoint available")
            self.recommendation_detail_var.set("Create a node to begin.")
            messagebox.showinfo("Recommend Next", "No checkpoint available.", parent=self.root)
            return
        reason = self.context.recommendation_engine.recommend_reason(
            self.context.graph,
            node,
        )
        self.canvas.select_node(node.id)
        self.context.pet_service.react_to_recommendation(node)
        self.canvas.redraw()
        self._render_pet()
        self._refresh_agenda()
        self.recommendation_var.set(f"Suggested next checkpoint: {node.title}")
        self.recommendation_detail_var.set(reason.replace(", ", "  \u00b7  "))
        self._set_status(f"Recommended: {node.title}")
        self.root.after_idle(self.fit_view)
        messagebox.showinfo(
            "Recommend Next",
            f"Next checkpoint: {node.title}\nReason: {reason}\nStatus: {node.status.value}\nPriority: P{node.priority}",
            parent=self.root,
        )

    def open_agent_dialog(self, node_id: str | None = None) -> None:
        existing_node_count = len(self.context.graph.nodes)
        dialog = AgentDialog(self.root, self.context, node_id=node_id)
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        if dialog.created_node_ids:
            if not dialog.layout_requested:
                self.context.graph_layout_service.apply_subset_grid_layout(
                    self.context.graph_service,
                    dialog.created_node_ids,
                )
            self.canvas.select_node(dialog.created_node_ids[0])
        self.canvas.redraw()
        if dialog.created_node_ids:
            if existing_node_count == 0:
                self.canvas.play_reveal(dialog.created_node_ids)
            else:
                self.canvas.spotlight_nodes(dialog.created_node_ids)
        self._refresh_agenda()
        self._update_recommendation_label()
        self._sync_pet_to_recommendation()
        status_parts: list[str] = []
        if dialog.created_node_ids:
            status_parts.append(f"{len(dialog.created_node_ids)} added")
        if dialog.deleted_node_ids:
            status_parts.append(f"{len(dialog.deleted_node_ids)} deleted")
        if dialog.updated_node_ids:
            status_parts.append(f"{len(dialog.updated_node_ids)} updated")
        if dialog.added_edge_ids:
            status_parts.append(f"{len(dialog.added_edge_ids)} edges")
        if dialog.layout_requested:
            status_parts.append("layout refreshed")
        self._set_status(
            "Agent plan applied"
            if not status_parts
            else f"Agent plan applied: {', '.join(status_parts)}"
        )
        self.root.after_idle(self.fit_view)

    def open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.root)
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        self._set_status("Settings saved")

    def show_review(self) -> None:
        summary = self.context.review_service.summary_text(self.context.graph)
        try:
            response = AgentClient.from_settings().complete_json(
                PromptBuilder().build_review_prompt(summary)
            )
            review_text = self.context.review_service.format_agent_review(
                response,
                fallback=summary,
            )
        except PetFlowError:
            review_text = summary
        messagebox.showinfo("Review", review_text, parent=self.root)
        self._set_status("Review generated")

    def capture_clipboard(self) -> None:
        capture = self.clipboard_watcher.capture_once(self.root.clipboard_get)
        if capture is None:
            self._set_status("Clipboard: no usable content")
            messagebox.showinfo("Clipboard", "No usable clipboard content.", parent=self.root)
            return
        x, y = self._next_node_position(NodeType.RESOURCE)
        resource_path = capture.content if capture.resource_type == "url" else ""
        node = self.context.graph_service.create_resource_node(
            title=capture.title,
            resource_type=capture.resource_type,
            resource_path=resource_path,
            description=capture.content,
            x=x,
            y=y,
        )
        self.canvas.select_node(node.id)
        self.canvas.redraw()
        self._set_status(f"Clipboard captured: {node.title}")

    def attach_file_to_selected_node(self, node_id: str | None = None) -> None:
        node_id = node_id or self.canvas.selected_node_id()
        if node_id is None:
            messagebox.showinfo("Attach File", "Select a node first.", parent=self.root)
            return
        path = filedialog.askopenfilename(parent=self.root)
        if not path:
            return
        try:
            node = self.context.graph_service.add_node_attachment(node_id, path)
            self.canvas.redraw()
            self._set_status(f"Attached file to {node.title}")
        except PetFlowError as exc:
            messagebox.showerror("Attach failed", str(exc), parent=self.root)

    def copy_selected_resource(self, node_id: str | None = None) -> None:
        node_id = node_id or self.canvas.selected_node_id()
        if node_id is None:
            messagebox.showinfo(
                "Copy Resource", "Select a resource node first.", parent=self.root
            )
            return
        node = self.context.graph.get_node(node_id)
        if node is None:
            return
        try:
            value = self.context.resource_service.resource_text(node)
        except PetFlowError as exc:
            messagebox.showerror("Copy resource failed", str(exc), parent=self.root)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self._set_status(f"Copied resource: {node.title}")

    def toggle_focus_mode(self) -> None:
        enabled = not bool(self.context.graph.workspace.focus_mode)
        self.focus_mode_var.set(enabled)
        self.context.graph.workspace.focus_mode = enabled
        if enabled:
            self.focus_started_at = datetime.now()
            current_node = self.context.graph.get_node(
                self.context.graph.workspace.current_node_id or ""
            )
            if current_node is None:
                self.context.graph.pet.state = PetStateType.ANGRY
                self.context.graph.pet.speech = "Select a focus node first."
                self.context.graph.pet.visible = True
                self.context.graph.pet.touch()
                self.canvas.redraw()
                self._render_pet()
            else:
                self.context.pet_service.move_to_node(
                    current_node.id,
                    speech=f"Focus: {current_node.title}",
                )
                self.canvas.redraw()
                self._render_pet()
            self._set_status("Focus mode: on")
        else:
            self.focus_started_at = None
            self._set_status("Focus mode: off")
        self._style_focus_button()
        self._refresh_focus_chip()

    def _update_recommendation_label(self) -> None:
        node = self.context.recommendation_engine.recommend_next(self.context.graph)
        if node is None:
            self.recommendation_var.set("Suggested next checkpoint: No checkpoint available")
            self.recommendation_detail_var.set("Create a node to begin.")
            return
        reason = self.context.recommendation_engine.recommend_reason(
            self.context.graph,
            node,
        )
        self.recommendation_var.set(f"Suggested next checkpoint: {node.title}")
        self.recommendation_detail_var.set(reason.replace(", ", "  \u00b7  "))

    def _refresh_agenda(self, preserve_scroll: bool = True) -> None:
        if self.agenda_panel is None:
            return
        scroll_fraction = 0.0
        if preserve_scroll:
            try:
                scroll_fraction = float(self.agenda_panel._canvas.yview()[0])
            except (AttributeError, tk.TclError, IndexError):
                scroll_fraction = 0.0
        self.agenda_panel.agenda_service = self.context.agenda_service
        self.agenda_panel.refresh(
            self.context.graph,
            saved_graphs=self._saved_graph_task_groups(),
        )
        if self._dark_mode:
            self._apply_current_theme_to(self.agenda_panel)
        if preserve_scroll:
            self.root.after_idle(lambda: self._restore_agenda_scroll(scroll_fraction))

    def _saved_graph_task_groups(self) -> list[SavedGraphTasks]:
        groups: list[SavedGraphTasks] = []
        for path in self._graph_slot_files():
            if self.current_graph_path == path:
                continue
            try:
                graph = self.context.storage_service.load_graph(path)
            except PetFlowError:
                continue
            nodes = tuple(
                sorted(
                    (
                        node
                        for node in graph.nodes.values()
                        if node.type != NodeType.RESOURCE
                    ),
                    key=lambda node: (
                        node.status.value == NodeStatus.DONE.value,
                        -node.priority,
                        node.title.casefold(),
                    ),
                )
            )
            groups.append(SavedGraphTasks(name=path.name, nodes=nodes))
        return groups

    def _restore_agenda_scroll(self, fraction: float) -> None:
        if self.agenda_panel is None:
            return
        try:
            self.agenda_panel._canvas.yview_moveto(max(0.0, min(1.0, fraction)))
        except (AttributeError, tk.TclError):
            return

    def _select_agenda_node(self, node_id: str) -> None:
        self.canvas.select_node(node_id)
        if self._edit_mode:
            self._ensure_right_panel_visible()
            self._show_right_tab("edit")
        node = self.context.graph.get_node(node_id)
        if node is not None:
            self._set_status(f"Selected: {node.title}")

    def _on_canvas_selection_changed(
        self, node_id: str | None, edge_id: str | None
    ) -> None:
        if self.inspector_panel is not None:
            self.inspector_panel.show_selection(node_id, edge_id)
        if self._edit_mode and (node_id is not None or edge_id is not None):
            self._ensure_right_panel_visible()
            self._show_right_tab("edit")
        if node_id is not None:
            node = self.context.graph.get_node(node_id)
            if node is not None:
                self._set_status(f"Selected node: {node.title}")
        elif edge_id is not None:
            self._set_status("Selected edge")

    def _focus_inspector_title(self, node_id: str) -> None:
        self._set_edit_mode(True)
        if self.inspector_panel is not None:
            self.inspector_panel.show_selection(node_id, None)
            self.root.after(20, self.inspector_panel.focus_title)

    def _on_inspector_graph_changed(self) -> None:
        # Inspector edits should not rebuild the Inspector or agenda list.
        # Rebuilding both panels causes visible flashing and loses the user's
        # exact in-panel editing position. Keep this path lightweight.
        self.canvas.redraw()
        self._update_recommendation_label()
        self._render_pet()

    def _change_node_status_from_inspector(
        self, node_id: str, status: NodeStatus
    ) -> None:
        try:
            self.context.graph_service.update_node_status(node_id, status)
            self.canvas.redraw()
            self._update_recommendation_label()
            self._render_pet()
            self._set_status(f"Node status: {status.value}")
        except PetFlowError as exc:
            messagebox.showerror("Update status failed", str(exc), parent=self.root)
            if self.inspector_panel is not None:
                self.inspector_panel.refresh(preserve_scroll=True)

    def _delete_node_from_inspector(self, node_id: str) -> None:
        self.canvas.select_node(node_id)
        self.canvas.delete_selected_node()

    def _delete_edge_from_inspector(self, edge_id: str) -> None:
        self.canvas.select_edge(edge_id)
        self.canvas.delete_selected_edge()

    def _advanced_edit_node(self, node_id: str) -> None:
        self.canvas.edit_node(node_id)

    def _advanced_edit_edge(self, edge_id: str) -> None:
        self.canvas.edit_edge(edge_id)

    def _on_canvas_graph_changed(self) -> None:
        self._refresh_agenda()
        self._update_recommendation_label()
        self._render_pet()

    def _sync_pet_to_recommendation(self) -> None:
        node = self.context.recommendation_engine.recommend_next(self.context.graph)
        self.context.pet_service.react_to_recommendation(node)
        self.canvas.redraw()
        self._render_pet()

    def _render_pet(self, reaction: str | None = None) -> None:
        if self.pet_panel is not None:
            self.pet_panel.render_pet(self.context.graph.pet, reaction)
            if self._dark_mode:
                self._apply_current_theme_to(self.pet_panel)

    def _apply_current_theme_to(self, widget: tk.Misc) -> None:
        bg = DARK_APP_BG if self._dark_mode else "#F6F8FB"
        panel = DARK_PANEL if self._dark_mode else "#FFFFFF"
        soft = DARK_PANEL_SOFT if self._dark_mode else "#EFF6FF"
        border = DARK_BORDER if self._dark_mode else "#E5E7EB"
        text = DARK_TEXT if self._dark_mode else "#111827"
        muted = DARK_MUTED if self._dark_mode else "#6B7280"
        self._apply_widget_theme(
            widget,
            panel=panel if widget is not self.root else bg,
            soft=soft,
            border=border,
            text=text,
            muted=muted,
        )

    def _refresh_focus_chip(self) -> None:
        if self.focus_chip is None:
            return
        if not self.context.graph.workspace.focus_mode:
            self.focus_chip.grid_remove()
            return
        current_node = self.context.graph.get_node(
            self.context.graph.workspace.current_node_id or ""
        )
        self.focus_time_var.set(self._focus_elapsed_text())
        self.focus_title_var.set(
            current_node.title[:28]
            if current_node is not None
            else "Choose a task to focus"
        )
        width = self.root.winfo_width()
        self.focus_chip.grid_remove()
        if width and width < 1080:
            self.focus_chip.grid(row=2, column=0, sticky="w", pady=(8, 0))
        else:
            self.focus_chip.grid(row=0, column=1, rowspan=2, sticky="e", padx=(18, 0))

    def _submit_pet_request(self, message: str, mode: str) -> None:
        if self.pet_panel is None or self._pet_agent_busy:
            return
        self._pet_agent_busy = True
        self.pet_panel.add_message("You", message)
        self.pet_panel.set_busy(True)
        self.context.graph.pet.state = PetStateType.THINK
        self.context.graph.pet.speech = (
            "Planning a workflow."
            if mode == "plan"
            else "Thinking about your question."
        )
        self.context.graph.pet.visible = True
        self.context.graph.pet.touch()
        self._render_pet()
        prompts = PromptBuilder()
        if mode == "plan":
            prompt = prompts.build_companion_planning_prompt(
                message, self.context.graph
            )
        else:
            prompt = prompts.build_companion_chat_prompt(message, self.context.graph)

        def request_plan() -> None:
            try:
                proposal = AgentClient.from_settings().complete_json(prompt)
                error: PetFlowError | None = None
            except PetFlowError as exc:
                proposal = None
                error = exc
            self._pet_agent_results.put((mode, proposal, error))

        Thread(target=request_plan, daemon=True).start()
        self.root.after(50, self._poll_pet_planning_result)

    def _poll_pet_planning_result(self) -> None:
        if not self._pet_agent_busy:
            return
        try:
            mode, proposal, error = self._pet_agent_results.get_nowait()
        except Empty:
            self.root.after(50, self._poll_pet_planning_result)
            return
        self._finish_pet_request(mode, proposal, error)

    def _finish_pet_request(
        self,
        mode: str,
        proposal: dict[str, object] | None,
        error: PetFlowError | None,
    ) -> None:
        self._pet_agent_busy = False
        if self.pet_panel is None:
            return
        self.pet_panel.set_busy(False)
        if error is not None or proposal is None:
            message = str(error) if error is not None else "No proposal returned."
            self.pet_panel.add_message("Pet", f"I could not plan that: {message}")
            self.context.graph.pet.state = PetStateType.ANGRY
            self.context.graph.pet.speech = message
            self._render_pet()
            return
        if mode == "chat":
            reply = proposal.get("reply")
            if not isinstance(reply, str) or not reply.strip():
                self.pet_panel.add_message(
                    "Pet", "The agent returned no readable answer."
                )
                return
            self.pet_panel.add_message("Pet", reply)
            self.context.graph.pet.state = PetStateType.HAPPY
            self.context.graph.pet.speech = reply
            self.context.graph.pet.touch()
            self._render_pet()
            self._set_status("Companion answered")
            return
        try:
            executor = AgentExecutor(
                self.context.graph_service,
                layout_service=self.context.graph_layout_service,
            )
            created = executor.apply_graph_proposal(proposal)
        except PetFlowError as exc:
            self.pet_panel.add_message("Pet", f"The proposed flow was invalid: {exc}")
            self.context.graph.pet.state = PetStateType.ANGRY
            self.context.graph.pet.speech = str(exc)
            self._render_pet()
            return
        if created and not executor.last_layout_requested:
            self.context.graph_layout_service.apply_grid_layout(
                self.context.graph_service
            )
        recommended = self.context.recommendation_engine.recommend_next(
            self.context.graph
        )
        self.context.pet_service.react_to_recommendation(recommended)
        if recommended is not None:
            self.canvas.select_node(recommended.id)
            next_text = f" First checkpoint: {recommended.title}."
        else:
            next_text = ""
        deleted_count = len(executor.last_deleted_node_ids)
        updated_count = len(executor.last_updated_node_ids)
        edge_count = len(executor.last_added_edge_ids)
        layout_text = " Layout refreshed." if executor.last_layout_requested else ""
        self.pet_panel.add_message(
            "Pet",
            (
                f"Agent plan updated with {len(created)} added, "
                f"{deleted_count} deleted, {updated_count} updated, "
                f"{edge_count} edges.{next_text}{layout_text}"
            ),
        )
        self.canvas.redraw()
        self._refresh_agenda()
        self._update_recommendation_label()
        self._render_pet()
        self._set_status(
            f"Agent plan updated: {len(created)} added, "
            f"{deleted_count} deleted, {updated_count} updated, {edge_count} edges"
        )
        self.root.after_idle(self.fit_view)

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.status_var.set(self._status_text())

    def _refresh_status_bar(self) -> None:
        self.status_var.set(self._status_text())
        self._refresh_focus_chip()
        self.status_after_id = self.root.after(1000, self._refresh_status_bar)

    def _status_text(self) -> str:
        parts = [
            self.status_message,
            f"Nodes: {len(self.context.graph.nodes)}",
            f"Edges: {len(self.context.graph.edges)}",
        ]
        current_node = self.context.graph.get_node(
            self.context.graph.workspace.current_node_id or ""
        )
        if current_node is not None:
            parts.append(f"Current: {current_node.title}")
        if self.context.graph.workspace.focus_mode:
            parts.append(f"Focus: {self._focus_elapsed_text()}")
            window_title = self.focus_monitor.current_window_title()
            if window_title:
                parts.append(f"Window: {window_title[:32]}")
        else:
            parts.append("Focus: off")
        return " | ".join(parts)

    def _focus_elapsed_text(self) -> str:
        if self.focus_started_at is None:
            return "on"
        elapsed = datetime.now() - self.focus_started_at
        total_seconds = max(0, int(elapsed.total_seconds()))
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _next_node_position(
        self, node_type: NodeType = NodeType.TASK
    ) -> tuple[float, float]:
        primary = [
            node
            for node in self.context.graph.nodes.values()
            if node.type not in {NodeType.RESOURCE, NodeType.REWARD}
        ]
        if node_type == NodeType.RESOURCE:
            resource_count = sum(
                node.type == NodeType.RESOURCE
                for node in self.context.graph.nodes.values()
            )
            return 120.0 + resource_count * 250.0, 290.0
        if node_type == NodeType.REWARD:
            return 120.0 + len(primary) * 250.0, 120.0
        return 120.0 + len(primary) * 250.0, 120.0

    def _save_session_state(self) -> None:
        slot_name = self._current_graph_slot_name() or ""
        try:
            SESSION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            SESSION_STATE_PATH.write_text(
                json.dumps({"current_slot": slot_name}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            return

    def _on_close(self) -> None:
        self._save_session_state()
        self.root.destroy()

    def run(self) -> None:
        try:
            self.root.mainloop()
        finally:
            self._save_session_state()
