from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from petflow.domain.entities import Edge, Node
from petflow.domain.enums import EdgeType, NodeStatus, NodeType, RepeatType


class NodeDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, node: Node | None = None) -> None:
        super().__init__(master)
        self.title("Edit Node" if node else "New Node")
        self.resizable(False, False)
        self.result: dict[str, object] | None = None

        self._title_var = tk.StringVar(value=node.title if node else "")
        self._description_var = tk.StringVar(value=node.description if node else "")
        self._type_var = tk.StringVar(
            value=(node.type.value if node else NodeType.TASK.value)
        )
        self._status_var = tk.StringVar(
            value=(node.status.value if node else NodeStatus.TODO.value)
        )
        self._priority_var = tk.IntVar(value=node.priority if node else 3)
        self._estimated_var = tk.IntVar(value=node.estimated_minutes if node else 30)
        self._repeat_type_var = tk.StringVar(
            value=(node.repeat_type.value if node else RepeatType.NONE.value)
        )
        self._next_due_var = tk.StringVar(value=node.next_due_at if node else "")
        self._streak_var = tk.IntVar(value=node.streak if node else 0)
        self._error_var = tk.StringVar(value="")

        self._build_ui()
        self.transient(master)
        self.grab_set()
        self._title_entry.focus_set()
        self.bind("<Return>", lambda _event: self._submit())
        self.bind("<Escape>", lambda _event: self._cancel())

    def _build_ui(self) -> None:
        body = ttk.Frame(self, padding=16)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Title").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self._title_entry = ttk.Entry(body, textvariable=self._title_var, width=36)
        self._title_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Description").grid(
            row=1, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(body, textvariable=self._description_var, width=36).grid(
            row=1, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(body, text="Type").grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(
            body,
            textvariable=self._type_var,
            values=[node_type.value for node_type in NodeType],
            state="readonly",
            width=34,
        ).grid(row=2, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Status").grid(row=3, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(
            body,
            textvariable=self._status_var,
            values=[status.value for status in NodeStatus],
            state="readonly",
            width=34,
        ).grid(row=3, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Priority").grid(row=4, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(
            body,
            from_=1,
            to=5,
            textvariable=self._priority_var,
            width=8,
        ).grid(row=4, column=1, sticky="w", pady=(0, 8))

        ttk.Label(body, text="Estimate").grid(row=5, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(
            body,
            from_=0,
            to=9999,
            textvariable=self._estimated_var,
            width=8,
        ).grid(row=5, column=1, sticky="w", pady=(0, 8))

        ttk.Label(body, text="Repeat").grid(row=6, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(
            body,
            textvariable=self._repeat_type_var,
            values=[repeat_type.value for repeat_type in RepeatType],
            state="readonly",
            width=34,
        ).grid(row=6, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Next Due").grid(row=7, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(body, textvariable=self._next_due_var, width=36).grid(
            row=7, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(body, text="Streak").grid(row=8, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(
            body,
            from_=0,
            to=9999,
            textvariable=self._streak_var,
            width=8,
        ).grid(row=8, column=1, sticky="w", pady=(0, 8))

        ttk.Label(body, textvariable=self._error_var, foreground="#dc2626").grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        actions = ttk.Frame(body)
        actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="OK", command=self._submit).pack(side="left")

    def _submit(self) -> None:
        try:
            title = self._title_var.get().strip()
            description = self._description_var.get().strip()
            priority = int(self._priority_var.get())
            estimated_minutes = int(self._estimated_var.get())
            streak = int(self._streak_var.get())
            if not title:
                raise ValueError("Title cannot be empty.")
            if priority < 1 or priority > 5:
                raise ValueError("Priority must be between 1 and 5.")
            if estimated_minutes < 0:
                raise ValueError("Estimate cannot be negative.")
            if streak < 0:
                raise ValueError("Streak cannot be negative.")
            self.result = {
                "title": title,
                "description": description,
                "node_type": NodeType(self._type_var.get()),
                "status": NodeStatus(self._status_var.get()),
                "priority": priority,
                "estimated_minutes": estimated_minutes,
                "repeat_type": RepeatType(self._repeat_type_var.get()),
                "next_due_at": self._next_due_var.get().strip(),
                "streak": streak,
            }
            self.destroy()
        except ValueError as exc:
            self._error_var.set(str(exc))

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class EdgeDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, edge: Edge | None = None) -> None:
        super().__init__(master)
        self.title("Edit Edge" if edge else "New Edge")
        self.resizable(False, False)
        self.result: dict[str, object] | None = None

        self._type_var = tk.StringVar(
            value=(edge.type.value if edge else EdgeType.DEPENDENCY.value)
        )
        self._label_var = tk.StringVar(value=edge.label if edge else "")
        self._error_var = tk.StringVar(value="")

        self._build_ui()
        self.transient(master)
        self.grab_set()
        self.bind("<Return>", lambda _event: self._submit())
        self.bind("<Escape>", lambda _event: self._cancel())

    def _build_ui(self) -> None:
        body = ttk.Frame(self, padding=16)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Type").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(
            body,
            textvariable=self._type_var,
            values=[edge_type.value for edge_type in EdgeType],
            state="readonly",
            width=28,
        ).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Label").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(body, textvariable=self._label_var, width=30).grid(
            row=1, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(body, textvariable=self._error_var, foreground="#dc2626").grid(
            row=2, column=0, columnspan=2, sticky="w"
        )

        actions = ttk.Frame(body)
        actions.grid(row=3, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="OK", command=self._submit).pack(side="left")

    def _submit(self) -> None:
        try:
            edge_type = EdgeType(self._type_var.get())
            label = self._label_var.get().strip()
            if len(label) > 80:
                raise ValueError("Label must be 80 characters or fewer.")
            self.result = {
                "type": edge_type,
                "label": label,
            }
            self.destroy()
        except ValueError as exc:
            self._error_var.set(str(exc))

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
