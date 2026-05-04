from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from petflow.agent.settings import AgentSettings
from petflow.domain.exceptions import PetFlowError


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
        self._mock_mode_var = tk.BooleanVar(value=settings.mock_mode)
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

        ttk.Checkbutton(
            body,
            text="Use mock mode",
            variable=self._mock_mode_var,
        ).grid(row=3, column=1, sticky="w", pady=(0, 8))

        ttk.Label(body, textvariable=self._error_var, foreground="#dc2626").grid(
            row=4, column=0, columnspan=2, sticky="w"
        )

        actions = ttk.Frame(body)
        actions.grid(row=5, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Save", command=self._save).pack(side="left")

    def _save(self) -> None:
        settings = AgentSettings(
            api_key=self._api_key_var.get().strip(),
            base_url=self._base_url_var.get().strip() or "https://api.openai.com/v1",
            model=self._model_var.get().strip() or "gpt-4o-mini",
            mock_mode=bool(self._mock_mode_var.get()),
        )
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
