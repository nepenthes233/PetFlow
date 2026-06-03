from __future__ import annotations

import tkinter as tk

from PIL import Image, ImageOps, ImageTk

from petflow.domain.entities import PetState
from petflow.domain.enums import PetStateType
from petflow.services.mascot_service import MascotConfig, MascotService
from petflow.ui.theme import BORDER, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY


class PetView:
    WIDTH = 260
    HEIGHT = 132
    MASCOT_SIZE = (88, 108)

    def __init__(
        self,
        canvas: tk.Canvas,
        font_family: str = "TkDefaultFont",
        mascot_id: str | None = None,
        mascot_service: MascotService | None = None,
    ) -> None:
        self.canvas = canvas
        self.font_family = font_family
        self._mascot_service = mascot_service or MascotService()
        self.mascot = self._mascot_service.load(mascot_id)
        self._image_cache: dict[str, ImageTk.PhotoImage | None] = {}

    def set_mascot_id(self, mascot_id: str | None) -> None:
        self.mascot = self._mascot_service.load(mascot_id)
        self._image_cache.clear()

    def draw(self, pet: PetState, reaction: str | None = None) -> None:
        self.canvas.delete("pet")
        if not pet.visible:
            return
        visual_state = self._visual_state(pet.state, reaction)
        mascot_image = self._image_for_state(visual_state)

        self.canvas.create_text(
            0,
            14,
            text="Status",
            anchor="w",
            fill=TEXT_MUTED,
            font=(self.font_family, 9),
            tags=("pet",),
        )
        self._pill(
            48,
            4,
            136,
            24,
            self._state_label(visual_state),
            "#F8FAFC",
            TEXT_SECONDARY,
        )

        if mascot_image is not None:
            self.canvas.create_image(
                0,
                22,
                image=mascot_image,
                anchor="nw",
                tags=("pet",),
            )
        else:
            face_fill = self._fill_for_state(visual_state)
            self.canvas.create_oval(
                0,
                40,
                44,
                84,
                fill=face_fill,
                outline=BORDER,
                width=1,
                tags=("pet",),
            )
            self._draw_face(visual_state, reaction)

        if visual_state == PetStateType.MOVE:
            self._draw_motion_marks()
        elif visual_state == PetStateType.HAPPY:
            self._draw_sparkles()

        self.canvas.create_text(
            102,
            44,
            text=self._message(pet.state, reaction),
            anchor="nw",
            justify="left",
            width=145,
            fill=TEXT_PRIMARY,
            font=(self.font_family, 10),
            tags=("pet",),
        )

    def _image_for_state(self, state: PetStateType) -> ImageTk.PhotoImage | None:
        asset_key = self._asset_key_for_state(state)
        if asset_key in self._image_cache:
            return self._image_cache[asset_key]

        path = self.mascot.asset_path(asset_key) if self.mascot is not None else None
        if path is None or not path.exists():
            self._image_cache[asset_key] = None
            return None

        size = self.mascot.size if self.mascot is not None else self.MASCOT_SIZE
        image = self._resize_mascot_image(Image.open(path).convert("RGBA"), size)
        photo = ImageTk.PhotoImage(image)
        self._image_cache[asset_key] = photo
        return photo

    @staticmethod
    def _resize_mascot_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
        resized = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        x = (size[0] - resized.width) // 2
        y = (size[1] - resized.height) // 2
        canvas.alpha_composite(resized, (x, y))
        return canvas

    @staticmethod
    def _asset_key_for_state(state: PetStateType) -> str:
        if state == PetStateType.HAPPY:
            return "complete"
        if state in {PetStateType.MOVE, PetStateType.THINK}:
            return "focused"
        return "idle"

    def _draw_face(self, state: PetStateType, reaction: str | None) -> None:
        eye_y = 56
        if state == PetStateType.HAPPY or reaction in {"complete", "arrive"}:
            self.canvas.create_arc(
                13, eye_y, 20, eye_y + 6, start=0, extent=180,
                style=tk.ARC, outline=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            self.canvas.create_arc(
                27, eye_y, 34, eye_y + 6, start=0, extent=180,
                style=tk.ARC, outline=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            self.canvas.create_arc(
                15, 61, 33, 76, start=195, extent=150,
                style=tk.ARC, outline=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            return
        if state == PetStateType.THINK:
            self.canvas.create_oval(
                15, eye_y, 19, eye_y + 4, fill=TEXT_PRIMARY, outline="", tags=("pet",)
            )
            self.canvas.create_oval(
                29, eye_y - 1, 33, eye_y + 3, fill=TEXT_PRIMARY, outline="", tags=("pet",)
            )
            self.canvas.create_line(
                17, 72, 31, 71, fill=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            return
        if state == PetStateType.ANGRY:
            self.canvas.create_line(
                12, 54, 20, 58, fill=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            self.canvas.create_line(
                28, 58, 36, 54, fill=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            self.canvas.create_line(
                17, 72, 31, 72, fill=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            return
        if state == PetStateType.SLEEP:
            self.canvas.create_line(
                13, 60, 20, 60, fill=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            self.canvas.create_line(
                28, 60, 35, 60, fill=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            self.canvas.create_arc(
                18, 67, 30, 78, start=20, extent=140,
                style=tk.ARC, outline=TEXT_PRIMARY, width=1, tags=("pet",)
            )
            return
        self.canvas.create_oval(
            15, eye_y, 20, eye_y + 5, fill=TEXT_PRIMARY, outline="", tags=("pet",)
        )
        self.canvas.create_oval(
            29, eye_y, 34, eye_y + 5, fill=TEXT_PRIMARY, outline="", tags=("pet",)
        )
        self.canvas.create_arc(
            16, 63, 33, 77, start=195, extent=150,
            style=tk.ARC, outline=TEXT_PRIMARY, width=1, tags=("pet",)
        )

    def _draw_sparkles(self) -> None:
        for x, y in ((72, 44), (92, 64), (84, 92)):
            self.canvas.create_line(
                x - 4, y, x + 4, y, fill="#F59E0B", width=2, tags=("pet",)
            )
            self.canvas.create_line(
                x, y - 4, x, y + 4, fill="#F59E0B", width=2, tags=("pet",)
            )

    def _draw_motion_marks(self) -> None:
        for y, length in ((58, 14), (72, 20), (86, 12)):
            self.canvas.create_line(
                86,
                y,
                86 + length,
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
            font=(self.font_family, 8),
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
            PetStateType.MOVE: "Tracking current focus.",
            PetStateType.HAPPY: "Progress recorded.",
            PetStateType.THINK: "Preparing a response.",
            PetStateType.ANGRY: "Select a task to start focus.",
            PetStateType.SLEEP: "Taking a quiet break.",
        }
        return messages[state]

    @staticmethod
    def _state_label(state: PetStateType) -> str:
        labels = {
            PetStateType.IDLE: "Idle",
            PetStateType.MOVE: "Focused",
            PetStateType.HAPPY: "Updated",
            PetStateType.THINK: "Waiting",
            PetStateType.ANGRY: "Needs task",
            PetStateType.SLEEP: "Quiet",
        }
        return labels[state]

    @staticmethod
    def _fill_for_state(state: PetStateType) -> str:
        if state == PetStateType.HAPPY:
            return "#D1FAE5"
        if state == PetStateType.THINK:
            return "#EDE9FE"
        if state == PetStateType.MOVE:
            return "#DBEAFE"
        if state == PetStateType.ANGRY:
            return "#FEF2F2"
        if state == PetStateType.SLEEP:
            return "#E2E8F0"
        return "#EFF6FF"
