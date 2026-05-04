from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from petflow.agent.agent_client import AgentClient
from petflow.agent.agent_executor import AgentExecutor
from petflow.agent.prompts import PromptBuilder
from petflow.app.app_context import AppContext
from petflow.domain.exceptions import PetFlowError


class AgentDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, context: AppContext, node_id: str | None = None) -> None:
        super().__init__(master)
        self.context = context
        self.node_id = node_id
        self.title("Agent")
        self.resizable(True, True)
        self.geometry("720x520")
        self.result: dict[str, object] | None = None

        initial_mode = "split" if node_id is not None else "generate"
        self._mode_var = tk.StringVar(value=initial_mode)
        self._goal_var = tk.StringVar(value=self._initial_input_text())
        self._preview_var = tk.StringVar(value="")
        self._client = AgentClient.from_settings()
        self._prompts = PromptBuilder()
        self._executor = AgentExecutor(self.context.graph_service)

        self._build_ui()
        self.transient(master)
        self.grab_set()
        self._refresh_preview()

    def _build_ui(self) -> None:
        body = ttk.Frame(self, padding=16)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        ttk.Label(body, text="Mode").grid(row=0, column=0, sticky="w", pady=(0, 8))
        mode_box = ttk.Combobox(
            body,
            textvariable=self._mode_var,
            values=["generate", "split"],
            state="readonly",
            width=20,
        )
        mode_box.grid(row=0, column=1, sticky="w", pady=(0, 8))
        mode_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh_preview())

        ttk.Label(body, text="Input").grid(row=1, column=0, sticky="nw", pady=(0, 8))
        ttk.Entry(body, textvariable=self._goal_var, width=80).grid(
            row=1, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Button(body, text="Refresh Preview", command=self._refresh_preview).grid(
            row=2, column=1, sticky="w", pady=(0, 8)
        )

        self._preview = tk.Text(body, wrap="word", height=18)
        self._preview.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 8))

        ttk.Label(body, textvariable=self._preview_var, foreground="#dc2626").grid(
            row=4, column=0, columnspan=2, sticky="w"
        )

        actions = ttk.Frame(body)
        actions.grid(row=5, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Apply", command=self._apply).pack(side="left")

    def _refresh_preview(self) -> None:
        try:
            proposal = self._build_proposal()
            preview = json.dumps(proposal, ensure_ascii=False, indent=2)
            self._set_preview(preview)
            self._preview_var.set("")
        except PetFlowError as exc:
            self._set_preview("")
            self._preview_var.set(str(exc))

    def _build_proposal(self) -> dict[str, object]:
        mode = self._mode_var.get()
        if mode == "split":
            node = self._resolve_node()
            prompt = self._prompts.build_node_split_prompt(self.context.graph, node)
        else:
            prompt = self._prompts.build_graph_generation_prompt(self._goal_var.get().strip())
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
            proposal = self._build_proposal()
            if self._mode_var.get() == "split":
                self._executor.apply_graph_proposal(proposal, parent_node_id=self.node_id)
            else:
                self._executor.apply_graph_proposal(proposal)
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

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
