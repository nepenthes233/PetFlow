from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from petflow.agent.agent_client import AgentClient
from petflow.agent.settings import AgentSettings
from petflow.domain.exceptions import PetFlowError
from petflow.services.mascot_service import MascotConfig, MascotService


class SettingsDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("Settings")
        self.resizable(False, False)
        self.result: AgentSettings | None = None

        try:
            settings = AgentSettings.load()
        except PetFlowError:
            settings = AgentSettings()
        self._api_key_var = tk.StringVar(value=settings.api_key)
        self._base_url_var = tk.StringVar(value=settings.base_url)
        self._model_var = tk.StringVar(value=settings.model)
        self._wire_api_var = tk.StringVar(value=settings.wire_api)
        self._mock_mode_var = tk.BooleanVar(value=settings.mock_mode)
        self._mascots = MascotService().list_configs()
        self._mascot_labels = self._mascot_label_map(self._mascots)
        self._mascot_var = tk.StringVar(
            value=self._label_for_mascot_id(settings.mascot_id)
        )
        self._error_var = tk.StringVar(value="")

        self._build_ui()
        self.transient(master)
        self.grab_set()

    def _build_ui(self) -> None:
        body = ttk.Frame(self, padding=16)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="API Key").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(
            body,
            textvariable=self._api_key_var,
            width=48,
            show="*",
        ).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Base URL").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(body, textvariable=self._base_url_var, width=48).grid(
            row=1, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(body, text="Model").grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(body, textvariable=self._model_var, width=48).grid(
            row=2, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(body, text="Wire API").grid(row=3, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(
            body,
            textvariable=self._wire_api_var,
            values=["chat_completions", "responses"],
            state="readonly",
            width=46,
        ).grid(row=3, column=1, sticky="ew", pady=(0, 8))

        ttk.Button(
            body,
            text="Use DeepSeek Defaults",
            command=self._use_deepseek_defaults,
        ).grid(row=4, column=1, sticky="w", pady=(0, 6))
        ttk.Label(
            body,
            text=(
                "OpenAI-compatible providers are supported. DeepSeek uses "
                "chat_completions with base URL https://api.deepseek.com. "
                "For DeepSeek, Test API probes model deepseek-v4-flash."
            ),
            foreground="#64748b",
            wraplength=390,
        ).grid(row=5, column=1, sticky="w", pady=(0, 8))

        ttk.Checkbutton(
            body,
            text="Use mock mode",
            variable=self._mock_mode_var,
        ).grid(row=6, column=1, sticky="w", pady=(0, 8))

        ttk.Label(body, text="Mascot Theme").grid(
            row=7, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Combobox(
            body,
            textvariable=self._mascot_var,
            values=list(self._mascot_labels),
            state="readonly",
            width=46,
        ).grid(row=7, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, textvariable=self._error_var, foreground="#dc2626").grid(
            row=8, column=0, columnspan=2, sticky="w"
        )

        actions = ttk.Frame(body)
        actions.grid(row=9, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Test API", command=self._test_api).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Save", command=self._save).pack(side="left")

    def _current_settings(self) -> AgentSettings:
        return AgentSettings(
            api_key=self._api_key_var.get().strip(),
            base_url=self._base_url_var.get().strip() or "https://api.openai.com/v1",
            model=self._model_var.get().strip() or "gpt-4o-mini",
            wire_api=self._wire_api_var.get() or "chat_completions",
            mock_mode=bool(self._mock_mode_var.get()),
            mascot_id=self._selected_mascot_id(),
        )

    @staticmethod
    def _mascot_label_map(configs: list[MascotConfig]) -> dict[str, str]:
        return {f"{config.name} ({config.id})": config.id for config in configs}

    def _label_for_mascot_id(self, mascot_id: str) -> str:
        for label, config_id in self._mascot_labels.items():
            if config_id == mascot_id:
                return label
        return next(iter(self._mascot_labels), "")

    def _selected_mascot_id(self) -> str:
        return self._mascot_labels.get(self._mascot_var.get(), "")

    def _use_deepseek_defaults(self) -> None:
        self._base_url_var.set("https://api.deepseek.com")
        self._model_var.set("deepseek-chat")
        self._wire_api_var.set("chat_completions")
        self._mock_mode_var.set(False)

    def _test_api(self) -> None:
        settings = self._current_settings()
        client = AgentClient.from_settings(settings)
        client.timeout_seconds = 10.0
        try:
            message = client.test_connection()
        except PetFlowError as exc:
            self._error_var.set(str(exc))
            messagebox.showerror("Agent API Test", str(exc), parent=self)
            return
        self._error_var.set("")
        messagebox.showinfo("Agent API Test", message, parent=self)

    def _save(self) -> None:
        settings = self._current_settings()
        try:
            settings.save()
        except PetFlowError as exc:
            self._error_var.set(str(exc))
            return
        self.result = settings
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
