from __future__ import annotations

import tkinter as tk

from petflow.domain.entities import PetState
from petflow.domain.enums import PetStateType


class PetView:
    WIDTH = 218
    HEIGHT = 184

    def __init__(
        self,
        canvas: tk.Canvas,
        font_family: str = "TkDefaultFont",
    ) -> None:
        self.canvas = canvas
        self.font_family = font_family

    def draw(self, pet: PetState, reaction: str | None = None) -> None:
        self.canvas.delete("pet")
        if not pet.visible:
            return
        visual_state = self._visual_state(pet.state, reaction)
        face_fill = self._fill_for_state(visual_state)

        self.canvas.create_text(
            14,
            16,
            text="COMPANION",
            anchor="w",
            fill="#6B7280",
            font=(self.font_family, 9, "bold"),
            tags=("pet",),
        )
        self._pill(
            143,
            7,
            204,
            27,
            visual_state.value.upper(),
            face_fill,
            "#475569",
        )

        self.canvas.create_oval(
            77,
            41,
            141,
            97,
            fill=face_fill,
            outline="#CBD5E1",
            width=2,
            tags=("pet",),
        )
        self._draw_face(visual_state, reaction)
        if reaction in {"complete", "arrive"}:
            self._draw_sparkles()
        elif reaction == "move":
            self._draw_motion_marks()

        self.canvas.create_text(
            109,
            120,
            text=self._message(pet.state, reaction),
            anchor="n",
            justify="center",
            width=190,
            fill="#374151",
            font=(self.font_family, 9),
            tags=("pet",),
        )

    def _draw_face(self, state: PetStateType, reaction: str | None) -> None:
        eye_y = 63
        if state == PetStateType.HAPPY or reaction in {"complete", "arrive"}:
            self.canvas.create_arc(
                91, eye_y, 101, eye_y + 8, start=0, extent=180,
                style=tk.ARC, outline="#1F2937", width=2, tags=("pet",)
            )
            self.canvas.create_arc(
                117, eye_y, 127, eye_y + 8, start=0, extent=180,
                style=tk.ARC, outline="#1F2937", width=2, tags=("pet",)
            )
            self.canvas.create_arc(
                97, 69, 121, 88, start=190, extent=160,
                style=tk.ARC, outline="#1F2937", width=2, tags=("pet",)
            )
            return
        if state == PetStateType.THINK:
            self.canvas.create_oval(
                93, eye_y, 98, eye_y + 5, fill="#1F2937", outline="", tags=("pet",)
            )
            self.canvas.create_oval(
                119, eye_y - 2, 125, eye_y + 4, fill="#1F2937", outline="", tags=("pet",)
            )
            self.canvas.create_line(
                101, 82, 117, 80, fill="#1F2937", width=2, tags=("pet",)
            )
            return
        if state == PetStateType.ANGRY:
            self.canvas.create_line(
                90, 60, 100, 65, fill="#1F2937", width=2, tags=("pet",)
            )
            self.canvas.create_line(
                118, 65, 128, 60, fill="#1F2937", width=2, tags=("pet",)
            )
            self.canvas.create_line(
                101, 83, 117, 83, fill="#1F2937", width=2, tags=("pet",)
            )
            return
        if state == PetStateType.SLEEP:
            self.canvas.create_line(
                91, 66, 100, 66, fill="#1F2937", width=2, tags=("pet",)
            )
            self.canvas.create_line(
                118, 66, 127, 66, fill="#1F2937", width=2, tags=("pet",)
            )
            self.canvas.create_arc(
                102, 74, 116, 86, start=20, extent=140,
                style=tk.ARC, outline="#1F2937", width=2, tags=("pet",)
            )
            return
        self.canvas.create_oval(
            93, eye_y, 99, eye_y + 6, fill="#1F2937", outline="", tags=("pet",)
        )
        self.canvas.create_oval(
            119, eye_y, 125, eye_y + 6, fill="#1F2937", outline="", tags=("pet",)
        )
        self.canvas.create_arc(
            99, 72, 119, 86, start=195, extent=150,
            style=tk.ARC, outline="#1F2937", width=2, tags=("pet",)
        )

    def _draw_sparkles(self) -> None:
        for x, y in ((68, 48), (151, 56), (148, 91)):
            self.canvas.create_line(
                x - 4, y, x + 4, y, fill="#F59E0B", width=2, tags=("pet",)
            )
            self.canvas.create_line(
                x, y - 4, x, y + 4, fill="#F59E0B", width=2, tags=("pet",)
            )

    def _draw_motion_marks(self) -> None:
        for y, length in ((57, 13), (69, 18), (81, 11)):
            self.canvas.create_line(
                57,
                y,
                57 + length,
                y,
                fill="#93C5FD",
                width=2,
                capstyle=tk.ROUND,
                tags=("pet",),
            )

    def _pill(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        text: str,
        fill: str,
        foreground: str,
    ) -> None:
        self._rounded_rectangle(
            x1, y1, x2, y2, 10, fill=fill, outline="", tags=("pet",)
        )
        self.canvas.create_text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            text=text,
            fill=foreground,
            font=(self.font_family, 8, "bold"),
            tags=("pet",),
        )

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
        return self.canvas.create_polygon(
            points, smooth=True, splinesteps=16, **kwargs
        )

    @staticmethod
    def _visual_state(state: PetStateType, reaction: str | None) -> PetStateType:
        if reaction in {"complete", "arrive"}:
            return PetStateType.HAPPY
        if reaction == "move":
            return PetStateType.MOVE
        return state

    @staticmethod
    def _message(state: PetStateType, reaction: str | None) -> str:
        if reaction == "complete":
            return "Task complete!\nNice work."
        if reaction == "move":
            return "Moving along the path\nto your next task."
        if reaction == "arrive":
            return "Next task ready.\nLet's continue."
        messages = {
            PetStateType.IDLE: "Ready when you are.",
            PetStateType.MOVE: "Staying with your\ncurrent focus.",
            PetStateType.HAPPY: "Progress recorded.\nReady to continue.",
            PetStateType.THINK: "Thinking about your\nnext move.",
            PetStateType.ANGRY: "Select a task before\nstarting focus mode.",
            PetStateType.SLEEP: "Taking a quiet break.",
        }
        return messages[state]

    @staticmethod
    def _fill_for_state(state: PetStateType) -> str:
        if state == PetStateType.HAPPY:
            return "#D1FAE5"
        if state == PetStateType.THINK:
            return "#EDE9FE"
        if state == PetStateType.MOVE:
            return "#DBEAFE"
        if state == PetStateType.ANGRY:
            return "#FEE2E2"
        if state == PetStateType.SLEEP:
            return "#E2E8F0"
        return "#FEF3C7"
