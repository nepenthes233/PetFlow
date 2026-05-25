from __future__ import annotations

from datetime import date, timedelta
import tkinter as tk
from tkinter import ttk

from petflow.domain.entities import Edge, Node
from petflow.domain.enums import (
    EdgeType,
    NodeStatus,
    NodeType,
    RepeatType,
    ResourceType,
)


class NodeDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, node: Node | None = None) -> None:
        super().__init__(master)
        self.title("Edit Node" if node else "New Node")
        self.resizable(True, True)
        self.geometry("560x780")
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
        self._actual_var = tk.IntVar(value=node.actual_minutes if node else 0)
        self._tags_var = tk.StringVar(value=", ".join(node.tags) if node else "")
        self._resource_type_var = tk.StringVar(
            value=(node.resource_type.value if node else ResourceType.URL.value)
        )
        self._resource_path_var = tk.StringVar(
            value=(node.resource_path if node else "")
        )
        self._checklist_text = "\n".join(
            item.text for item in node.checklist
        ) if node else ""
        self._repeat_type_var = tk.StringVar(
            value=(node.repeat_type.value if node else RepeatType.NONE.value)
        )
        self._repeat_interval_var = tk.IntVar(
            value=(node.repeat_interval if node else 1)
        )
        self._next_due_var = tk.StringVar(
            value=(node.next_due_at[:10] if node and node.next_due_at else "")
        )
        self._streak_var = tk.IntVar(value=node.streak if node else 0)
        self._error_var = tk.StringVar(value="")
        self._attachments = list(node.attachments) if node else []

        self._build_ui()
        self.transient(master)
        self.grab_set()
        self._title_entry.focus_set()
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

        ttk.Label(body, text="Actual").grid(row=6, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(
            body,
            from_=0,
            to=9999,
            textvariable=self._actual_var,
            width=8,
        ).grid(row=6, column=1, sticky="w", pady=(0, 8))

        ttk.Label(body, text="Tags").grid(row=7, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(body, textvariable=self._tags_var, width=36).grid(
            row=7, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(body, text="Resource Type").grid(
            row=8, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Combobox(
            body,
            textvariable=self._resource_type_var,
            values=[resource_type.value for resource_type in ResourceType],
            state="readonly",
            width=34,
        ).grid(row=8, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Resource Path").grid(
            row=9, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(body, textvariable=self._resource_path_var, width=36).grid(
            row=9, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(body, text="Checklist").grid(
            row=10, column=0, sticky="nw", pady=(0, 8)
        )
        self._checklist_entry = tk.Text(body, height=4, width=36, wrap="word")
        self._checklist_entry.insert("1.0", self._checklist_text)
        self._checklist_entry.grid(row=10, column=1, sticky="ew", pady=(0, 8))

        schedule = ttk.LabelFrame(body, text="Schedule", padding=(12, 10))
        schedule.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(6, 12))
        schedule.columnconfigure(1, weight=1)

        ttk.Label(schedule, text="Date").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(schedule, textvariable=self._next_due_var, width=20).grid(
            row=0, column=1, sticky="w", pady=(0, 8)
        )
        date_actions = ttk.Frame(schedule)
        date_actions.grid(row=1, column=1, sticky="w", pady=(0, 10))
        ttk.Button(
            date_actions,
            text="Today",
            command=lambda: self._set_due_date(0),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            date_actions,
            text="Tomorrow",
            command=lambda: self._set_due_date(1),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            date_actions,
            text="+7 Days",
            command=lambda: self._set_due_date(7),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            date_actions,
            text="Clear",
            command=lambda: self._next_due_var.set(""),
        ).pack(side="left")

        ttk.Label(schedule, text="Repeats").grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(
            schedule,
            textvariable=self._repeat_type_var,
            values=[repeat_type.value for repeat_type in RepeatType],
            state="readonly",
            width=18,
        ).grid(row=2, column=1, sticky="w", pady=(0, 8))

        ttk.Label(schedule, text="Every").grid(row=3, column=0, sticky="w")
        interval = ttk.Frame(schedule)
        interval.grid(row=3, column=1, sticky="w")
        ttk.Spinbox(
            interval,
            from_=1,
            to=365,
            textvariable=self._repeat_interval_var,
            width=6,
        ).pack(side="left")
        ttk.Label(interval, text="cycle(s)").pack(side="left", padx=(8, 0))
        ttk.Label(
            schedule,
            text="Use YYYY-MM-DD. Repeating items appear on each occurrence.",
            foreground="#64748b",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ttk.Label(body, text="Streak").grid(row=12, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(
            body,
            from_=0,
            to=9999,
            textvariable=self._streak_var,
            width=8,
        ).grid(row=12, column=1, sticky="w", pady=(0, 8))

        ttk.Label(body, text="Attachments").grid(
            row=13, column=0, sticky="nw", pady=(0, 8)
        )
        ttk.Label(
            body,
            text=self._attachments_text(),
            wraplength=280,
            foreground="#475569",
        ).grid(row=13, column=1, sticky="w", pady=(0, 8))

        ttk.Label(body, textvariable=self._error_var, foreground="#dc2626").grid(
            row=14, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        actions = ttk.Frame(body)
        actions.grid(row=15, column=0, columnspan=2, sticky="e", pady=(16, 0))
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
            actual_minutes = int(self._actual_var.get())
            streak = int(self._streak_var.get())
            repeat_interval = int(self._repeat_interval_var.get())
            next_due_at = self._next_due_var.get().strip()
            if not title:
                raise ValueError("Title cannot be empty.")
            if priority < 1 or priority > 5:
                raise ValueError("Priority must be between 1 and 5.")
            if estimated_minutes < 0:
                raise ValueError("Estimate cannot be negative.")
            if actual_minutes < 0:
                raise ValueError("Actual minutes cannot be negative.")
            if streak < 0:
                raise ValueError("Streak cannot be negative.")
            if repeat_interval < 1:
                raise ValueError("Repeat interval must be at least 1.")
            if next_due_at:
                try:
                    date.fromisoformat(next_due_at)
                except ValueError as exc:
                    raise ValueError("Date must use YYYY-MM-DD.") from exc
            checklist = [
                line.strip()
                for line in self._checklist_entry.get("1.0", tk.END).splitlines()
                if line.strip()
            ]
            self.result = {
                "title": title,
                "description": description,
                "node_type": NodeType(self._type_var.get()),
                "status": NodeStatus(self._status_var.get()),
                "priority": priority,
                "estimated_minutes": estimated_minutes,
                "actual_minutes": actual_minutes,
                "tags": self._parse_tags(self._tags_var.get()),
                "resource_type": ResourceType(self._resource_type_var.get()),
                "resource_path": self._resource_path_var.get().strip(),
                "checklist": checklist,
                "repeat_type": RepeatType(self._repeat_type_var.get()),
                "repeat_interval": repeat_interval,
                "next_due_at": next_due_at,
                "streak": streak,
            }
            self.destroy()
        except ValueError as exc:
            self._error_var.set(str(exc))

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def _attachments_text(self) -> str:
        if not self._attachments:
            return "-"
        return "\n".join(self._attachments)

    def _set_due_date(self, offset: int) -> None:
        self._next_due_var.set((date.today() + timedelta(days=offset)).isoformat())

    @staticmethod
    def _parse_tags(value: str) -> list[str]:
        tags: list[str] = []
        for raw_tag in value.split(","):
            tag = raw_tag.strip()
            if tag and tag not in tags:
                tags.append(tag)
        return tags


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
