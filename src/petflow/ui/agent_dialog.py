from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from petflow.agent.agent_client import AgentClient
from petflow.agent.agent_executor import AgentExecutor
from petflow.agent.prompts import PromptBuilder
from petflow.agent.proposal import AgentProposalValidator
from petflow.app.app_context import AppContext
from petflow.domain.exceptions import PetFlowError
from petflow.ui.components import TextButton
from petflow.ui.fonts import get_ui_font_family
from petflow.ui.theme import (
    BACKGROUND,
    BORDER,
    DARK_APP_BG,
    DARK_BORDER,
    DARK_MUTED,
    DARK_PANEL,
    DARK_PANEL_SOFT,
    DARK_SURFACE,
    DARK_TEXT,
    DARK_TEXT_SECONDARY,
    PRIMARY,
    SURFACE,
    SURFACE_SUBTLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class AgentDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        context: AppContext,
        node_id: str | None = None,
    ) -> None:
        super().__init__(master)
        self.context = context
        self.node_id = node_id
        self._dark_mode = self.context.graph.workspace.theme == "dark"
        self._bg = DARK_APP_BG if self._dark_mode else BACKGROUND
        self._surface = DARK_SURFACE if self._dark_mode else SURFACE
        self._soft = DARK_PANEL_SOFT if self._dark_mode else SURFACE_SUBTLE
        self._border = DARK_BORDER if self._dark_mode else BORDER
        self._text = DARK_TEXT if self._dark_mode else TEXT_PRIMARY
        self._secondary = DARK_TEXT_SECONDARY if self._dark_mode else TEXT_SECONDARY
        self._muted = DARK_MUTED if self._dark_mode else TEXT_MUTED
        self.title("Agent Planner")
        self.configure(bg=self._bg)
        self.resizable(True, True)
        self.geometry("820x680")
        self.minsize(720, 580)
        self.result: dict[str, object] | None = None
        self.font_family = get_ui_font_family(self)

        initial_mode = "split" if node_id is not None else "generate"
        self._mode_var = tk.StringVar(value=initial_mode)
        self._goal_var = tk.StringVar(value=self._initial_input_text())
        self._preview_var = tk.StringVar(value="")
        self._client = AgentClient.from_settings()
        self._prompts = PromptBuilder()
        self._executor = AgentExecutor(self.context.graph_service)
        self._validator = AgentProposalValidator()
        self._proposal: dict[str, object] | None = None
        self.created_node_ids: list[str] = []
        self.deleted_node_ids: list[str] = []
        self.updated_node_ids: list[str] = []
        self.added_edge_ids: list[str] = []
        self.layout_requested = False

        self._build_ui()
        self.transient(master)
        self.grab_set()
        self._refresh_preview()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.configure(
            "PetFlow.TCombobox",
            padding=(8, 6),
            fieldbackground=self._soft,
            background=self._soft,
            foreground=self._text,
            arrowcolor=self._muted,
        )

        body = tk.Frame(self, bg=self._bg, padx=24, pady=22)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        tk.Label(
            body,
            text="Agent Planner",
            bg=self._bg,
            fg=self._text,
            font=(self.font_family, 18, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            body,
            text=(
                "Describe a pet-care goal. Companion will turn it into "
                "concrete graph changes."
            ),
            bg=self._bg,
            fg=self._muted,
            font=(self.font_family, 10),
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        input_card = tk.Frame(
            body,
            bg=self._surface,
            padx=16,
            pady=16,
            highlightthickness=1,
            highlightbackground=self._border,
        )
        input_card.grid(row=2, column=0, sticky="nsew")
        input_card.columnconfigure(0, weight=1)
        input_card.rowconfigure(3, weight=1)

        controls = tk.Frame(input_card, bg=self._surface)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)
        tk.Label(
            controls,
            text="Mode",
            bg=self._surface,
            fg=self._secondary,
            font=(self.font_family, 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))
        mode_box = ttk.Combobox(
            controls,
            textvariable=self._mode_var,
            values=["generate", "split"],
            state="readonly",
            width=18,
            style="PetFlow.TCombobox",
        )
        mode_box.grid(row=0, column=1, sticky="w")
        mode_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh_preview())
        TextButton(
            controls,
            "Generate Preview",
            self._refresh_preview,
            self.font_family,
            variant="secondary",
        ).grid(row=0, column=2, sticky="e")

        tk.Label(
            input_card,
            text="Goal",
            bg=self._surface,
            fg=self._secondary,
            font=(self.font_family, 10, "bold"),
        ).grid(row=1, column=0, sticky="w", pady=(14, 6))
        goal_entry = tk.Entry(
            input_card,
            textvariable=self._goal_var,
            bg=self._soft,
            fg=self._text,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self._border,
            highlightcolor=self._border,
            insertbackground=self._text,
            font=(self.font_family, 11),
        )
        goal_entry.grid(row=2, column=0, sticky="ew", ipady=8)

        preview_shell = tk.Frame(input_card, bg=self._surface)
        preview_shell.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        preview_shell.columnconfigure(0, weight=1)
        preview_shell.rowconfigure(1, weight=3)
        preview_shell.rowconfigure(3, weight=2)
        tk.Label(
            preview_shell,
            text="Plan preview",
            bg=self._surface,
            fg=self._secondary,
            font=(self.font_family, 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self._preview = tk.Text(
            preview_shell,
            wrap="word",
            height=10,
            bg=self._soft,
            fg=self._secondary,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self._border,
            padx=12,
            pady=10,
            font=(self.font_family, 10),
        )
        self._preview.grid(row=1, column=0, sticky="nsew")

        tk.Label(
            preview_shell,
            text="Advanced: Raw JSON",
            bg=self._surface,
            fg=self._muted,
            font=(self.font_family, 9, "bold"),
        ).grid(row=2, column=0, sticky="w", pady=(12, 6))
        self._raw_preview = tk.Text(
            preview_shell,
            wrap="none",
            height=7,
            bg=self._soft,
            fg=self._muted,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self._border,
            padx=12,
            pady=10,
            font=("Consolas", 9),
        )
        self._raw_preview.grid(row=3, column=0, sticky="nsew")

        tk.Label(body, textvariable=self._preview_var, bg=self._bg, fg="#DC2626").grid(
            row=3, column=0, sticky="w", pady=(10, 0)
        )

        actions = tk.Frame(body, bg=self._bg)
        actions.grid(row=4, column=0, sticky="e", pady=(16, 0))
        TextButton(
            actions,
            "Cancel",
            self._cancel,
            self.font_family,
            variant="secondary",
        ).pack(side="left", padx=(0, 8))
        TextButton(
            actions,
            "Apply Plan",
            self._apply,
            self.font_family,
            variant="primary",
        ).pack(side="left")
        if self._dark_mode:
            self._apply_dark_to_children(self)

    def _apply_dark_to_children(self, widget: tk.Misc) -> None:
        try:
            cls = widget.winfo_class()
            if cls in {"Frame", "LabelFrame"}:
                widget.configure(bg=self._surface if widget is not self else self._bg)
            elif cls == "Label":
                widget.configure(bg=str(widget.master.cget("bg")), fg=self._text)
            elif cls == "Button":
                is_primary = str(widget.cget("bg")).lower() == PRIMARY.lower()
                if not is_primary:
                    widget.configure(
                        bg=self._soft,
                        fg=self._text,
                        activebackground=self._border,
                        activeforeground=self._text,
                        highlightbackground=self._border,
                    )
            elif cls in {"Entry", "Text"}:
                widget.configure(
                    bg=self._soft,
                    fg=self._text,
                    insertbackground=self._text,
                    highlightbackground=self._border,
                    highlightcolor=self._border,
                    selectbackground="#1E3A5F",
                    selectforeground=self._text,
                )
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._apply_dark_to_children(child)

    def _refresh_preview(self) -> None:
        try:
            proposal = self._build_proposal()
            validated = self._validator.validate(proposal)
            self._proposal = validated
            self._set_preview(self._format_summary(validated))
            self._set_raw_preview(json.dumps(proposal, ensure_ascii=False, indent=2))
            self._preview_var.set("")
        except PetFlowError as exc:
            self._proposal = None
            self._set_preview("")
            self._set_raw_preview("")
            self._preview_var.set(str(exc))

    def _build_proposal(self) -> dict[str, object]:
        mode = self._mode_var.get()
        if mode == "split":
            node = self._resolve_node()
            prompt = self._prompts.build_node_split_prompt(self.context.graph, node)
        else:
            prompt = self._prompts.build_companion_planning_prompt(
                self._goal_var.get().strip(),
                self.context.graph,
            )
        return self._client.complete_json(prompt)

    def _initial_input_text(self) -> str:
        if self.node_id is None:
            return ""
        node = self.context.graph.get_node(self.node_id)
        if node is None:
            return ""
        return node.title

    def _apply(self) -> None:
        try:
            proposal = self._proposal or self._build_proposal()
            if self._mode_var.get() == "split":
                created = self._executor.apply_graph_proposal(
                    proposal,
                    parent_node_id=self.node_id,
                )
            else:
                created = self._executor.apply_graph_proposal(proposal)
            self.created_node_ids = [node.id for node in created]
            self.deleted_node_ids = list(self._executor.last_deleted_node_ids)
            self.updated_node_ids = list(self._executor.last_updated_node_ids)
            self.added_edge_ids = list(self._executor.last_added_edge_ids)
            self.layout_requested = self._executor.last_layout_requested
            self.result = proposal
            self.destroy()
        except PetFlowError as exc:
            self._preview_var.set(str(exc))

    def _resolve_node(self):
        if self.node_id is None:
            raise PetFlowError("Split mode requires a node selection.")
        node = self.context.graph.get_node(self.node_id)
        if node is None:
            raise PetFlowError("Selected node no longer exists.")
        return node

    def _set_preview(self, content: str) -> None:
        self._preview.configure(state="normal")
        self._preview.delete("1.0", tk.END)
        self._preview.insert("1.0", content)
        self._preview.configure(state="disabled")

    @staticmethod
    def _format_summary(proposal: dict[str, object]) -> str:
        nodes = proposal.get("nodes", [])
        edges = proposal.get("edges", [])
        update_nodes = proposal.get("update_nodes", [])
        add_edges = proposal.get("add_edges", [])
        delete_node_ids = proposal.get("delete_node_ids", [])
        delete_all_nodes = bool(proposal.get("delete_all_nodes", False))
        delete_query = str(proposal.get("delete_query", "")).strip()
        layout = proposal.get("layout", {})
        layout_enabled = isinstance(layout, dict) and bool(layout.get("enabled"))
        lines = [
            f"Nodes: {len(nodes)}",
        ]
        if isinstance(nodes, list):
            for node in nodes:
                if isinstance(node, dict):
                    extras = []
                    if node.get("next_due_at"):
                        extras.append(f"due {node.get('next_due_at')}")
                    repeat_type = node.get("repeat_type")
                    if repeat_type and repeat_type != "none":
                        extras.append(f"repeats {repeat_type}")
                    suffix = f" · {', '.join(extras)}" if extras else ""
                    lines.append(
                        f"- {node.get('title', '')} [{node.get('type', 'task')}] "
                        f"P{node.get('priority', 3)} "
                        f"{node.get('estimated_minutes', 30)}m{suffix}"
                    )
        lines.append("")
        lines.append(f"Edges: {len(edges)}")
        if isinstance(edges, list):
            for edge in edges:
                if isinstance(edge, dict):
                    label = edge.get("label") or edge.get("type", "dependency")
                    lines.append(
                        f"- {edge.get('source', '')} -> "
                        f"{edge.get('target', '')} ({label})"
                    )
        lines.append("")
        lines.append(f"Update nodes: {len(update_nodes)}")
        if isinstance(update_nodes, list):
            for update in update_nodes:
                if isinstance(update, dict):
                    target = update.get("node_id") or update.get("query")
                    changes = update.get("changes", {})
                    fields = ", ".join(changes) if isinstance(changes, dict) else ""
                    lines.append(f"- {target}: {fields}")
        lines.append("")
        lines.append(f"Add edges: {len(add_edges)}")
        if isinstance(add_edges, list):
            for edge in add_edges:
                if isinstance(edge, dict):
                    source = edge.get("source") or edge.get("source_query")
                    target = edge.get("target") or edge.get("target_query")
                    label = edge.get("label") or edge.get("type", "dependency")
                    lines.append(f"- {source} -> {target} ({label})")
        lines.append("")
        lines.append(f"Delete nodes: {len(delete_node_ids)}")
        if delete_all_nodes:
            lines.append("- all nodes")
        if delete_query:
            lines.append(f"- matching: {delete_query}")
        if isinstance(delete_node_ids, list):
            for node_id in delete_node_ids:
                lines.append(f"- {node_id}")
        lines.append("")
        lines.append(f"Layout: {'yes' if layout_enabled else 'no'}")
        return "\n".join(lines)

    def _set_raw_preview(self, content: str) -> None:
        self._raw_preview.configure(state="normal")
        self._raw_preview.delete("1.0", tk.END)
        self._raw_preview.insert("1.0", content)
        self._raw_preview.configure(state="disabled")

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
