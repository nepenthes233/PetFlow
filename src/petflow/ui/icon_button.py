from __future__ import annotations

from collections.abc import Callable
import math
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk

from petflow.ui.theme import (
    BORDER,
    COLOR_BG,
    COLOR_BUTTON_HOVER,
    COLOR_PANEL,
    COLOR_PRIMARY,
    COLOR_PRIMARY_DARK,
    COLOR_TOOLTIP_BORDER,
    COLOR_TOOLTIP_TEXT,
    PRIMARY_SOFT,
    TEXT_SECONDARY,
)


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 300) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def set_text(self, text: str) -> None:
        self.text = text
        if self._window is not None:
            self._hide()

    def _schedule(self, _event: tk.Event | None = None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is None:
            return
        try:
            self.widget.after_cancel(self._after_id)
        except tk.TclError:
            pass
        self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        if not self.text or self._window is not None:
            return
        window = tk.Toplevel(self.widget)
        window.withdraw()
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        shell = tk.Frame(
            window,
            bg=COLOR_TOOLTIP_BORDER,
            padx=1,
            pady=1,
        )
        shell.pack()
        label = tk.Label(
            shell,
            text=self.text,
            bg=COLOR_PANEL,
            fg=COLOR_TOOLTIP_TEXT,
            padx=10,
            pady=6,
            font=("TkDefaultFont", 10),
            relief="flat",
            borderwidth=0,
        )
        label.pack()
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        window.update_idletasks()
        x -= window.winfo_width() // 2
        window.geometry(f"+{max(4, x)}+{max(4, y)}")
        window.deiconify()
        self._window = window

    def _hide(self, _event: tk.Event | None = None) -> None:
        self._cancel()
        if self._window is None:
            return
        try:
            self._window.destroy()
        except tk.TclError:
            pass
        self._window = None


class IconButton(tk.Button):
    SIZE = 38
    ICON_SIZE = 22

    def __init__(
        self,
        master: tk.Misc,
        icon: str,
        tooltip: str,
        command: Callable[[], None],
        *,
        primary: bool = False,
        selected: bool = False,
        size: int = SIZE,
    ) -> None:
        self.icon_name = icon
        self.tooltip_text = tooltip
        self.primary = primary
        self.selected = selected
        self.dark_mode = False
        self._normal_image: ImageTk.PhotoImage | None = None
        self._active_image: ImageTk.PhotoImage | None = None
        self._disabled_image: ImageTk.PhotoImage | None = None
        self._hover_image: ImageTk.PhotoImage | None = None
        self._build_images()
        super().__init__(
            master,
            image=self._normal_image,
            command=command,
            width=size,
            height=size,
            bg=self._bg(),
            activebackground=self._active_bg(),
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
            cursor="hand2",
            takefocus=0,
        )
        self.tooltip = Tooltip(self, tooltip)
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")

    def set_selected(self, selected: bool) -> None:
        if self.selected == selected:
            return
        self.selected = selected
        self._build_images()
        self.configure(
            image=self._normal_image,
            bg=self._bg(),
            activebackground=self._active_bg(),
            highlightbackground=COLOR_PRIMARY if selected else self._border(),
        )

    def set_tooltip(self, text: str) -> None:
        self.tooltip_text = text
        self.tooltip.set_text(text)

    def set_dark_mode(self, enabled: bool) -> None:
        if self.dark_mode == enabled:
            return
        self.dark_mode = enabled
        self._build_images()
        self.configure(
            image=self._normal_image,
            bg=self._bg(),
            activebackground=self._active_bg(),
            highlightbackground=COLOR_PRIMARY if self.selected else self._border(),
            highlightcolor=self._border(),
        )

    def set_busy(self, busy: bool) -> None:
        self.configure(
            state="disabled" if busy else "normal",
            image=self._disabled_image if busy else self._normal_image,
            cursor="arrow" if busy else "hand2",
        )

    def _bg(self) -> str:
        if self.primary:
            return COLOR_PRIMARY
        if self.selected:
            return "#1E3A5F" if self.dark_mode else PRIMARY_SOFT
        return "#111B21" if self.dark_mode else COLOR_PANEL

    def _active_bg(self) -> str:
        if self.primary:
            return COLOR_PRIMARY_DARK
        if self.selected:
            return "#1E3A5F" if self.dark_mode else PRIMARY_SOFT
        return "#1F2C34" if self.dark_mode else COLOR_BUTTON_HOVER

    def _fg(self) -> str:
        if self.primary:
            return COLOR_PANEL
        if self.selected:
            return "#93C5FD" if self.dark_mode else COLOR_PRIMARY
        return "#CBD5E1" if self.dark_mode else TEXT_SECONDARY

    def _border(self) -> str:
        return "#26343D" if self.dark_mode else BORDER

    def _build_images(self) -> None:
        bg = self._bg()
        fg = self._fg()
        self._normal_image = ImageTk.PhotoImage(_draw_icon(self.icon_name, fg, bg))
        self._active_image = ImageTk.PhotoImage(
            _draw_icon(self.icon_name, fg, self._active_bg())
        )
        self._hover_image = ImageTk.PhotoImage(
            _draw_icon(self.icon_name, fg, self._active_bg())
        )
        self._disabled_image = ImageTk.PhotoImage(
            _draw_icon(self.icon_name, "#64748B", "#0B141A" if self.dark_mode else COLOR_BG)
        )

    def _on_enter(self, _event: tk.Event) -> None:
        if str(self.cget("state")) == "normal":
            self.configure(image=self._hover_image, bg=self._active_bg())

    def _on_leave(self, _event: tk.Event) -> None:
        self.configure(image=self._normal_image, bg=self._bg())


def _draw_icon(name: str, fg: str, bg: str) -> Image.Image:
    scale = 4
    size = IconButton.ICON_SIZE
    image = Image.new("RGBA", (size * scale, size * scale), bg)
    draw = ImageDraw.Draw(image)

    def xy(values: tuple[float, ...]) -> tuple[int, ...]:
        return tuple(int(round(value * scale)) for value in values)

    def line(points: list[tuple[float, float]], width: int = 2) -> None:
        draw.line([(x * scale, y * scale) for x, y in points], fill=fg, width=width * scale, joint="curve")

    def rect(values: tuple[float, float, float, float], width: int = 2) -> None:
        draw.rounded_rectangle(xy(values), radius=3 * scale, outline=fg, width=width * scale)

    def fill_rect(values: tuple[float, float, float, float]) -> None:
        draw.rounded_rectangle(xy(values), radius=2 * scale, fill=fg)

    def ellipse(values: tuple[float, float, float, float], width: int = 2) -> None:
        draw.ellipse(xy(values), outline=fg, width=width * scale)

    if name == "node-add":
        rect((3, 5, 14, 16))
        line([(16, 7), (16, 15)])
        line([(12, 11), (20, 11)])
    elif name == "edge-add":
        ellipse((2, 3, 8, 9))
        ellipse((14, 13, 20, 19))
        line([(7, 8), (15, 14)])
    elif name == "complete":
        ellipse((3, 3, 19, 19))
        line([(7, 11), (10, 14), (16, 8)])
    elif name == "edit":
        line([(5, 16), (15, 6)], 3)
        line([(13, 4), (18, 9)], 3)
        line([(4, 18), (9, 17)])
    elif name == "save":
        rect((4, 3, 18, 19))
        fill_rect((7, 4, 15, 9))
        rect((7, 13, 15, 19), 1)
    elif name == "load":
        line([(3, 7), (8, 7), (10, 10), (19, 10), (17, 18), (4, 18), (3, 7)])
    elif name == "sample":
        rect((4, 5, 18, 17))
        line([(8, 5), (8, 17)], 1)
        line([(14, 5), (14, 17)], 1)
        line([(4, 11), (18, 11)], 1)
    elif name == "recommend":
        ellipse((4, 4, 18, 18))
        ellipse((8, 8, 14, 14))
        line([(14, 8), (19, 3)])
    elif name == "agent":
        rect((4, 7, 18, 18))
        line([(11, 7), (11, 3)])
        ellipse((9, 1, 13, 5), 1)
        draw.ellipse(xy((7, 11, 9, 13)), fill=fg)
        draw.ellipse(xy((13, 11, 15, 13)), fill=fg)
    elif name == "arrange":
        for x, y in ((4, 4), (14, 4), (4, 14), (14, 14)):
            rect((x, y, x + 4, y + 4), 1)
        line([(8, 6), (14, 6)], 1)
        line([(6, 8), (6, 14)], 1)
        line([(16, 8), (16, 14)], 1)
    elif name == "fit":
        line([(4, 9), (4, 4), (9, 4)])
        line([(13, 4), (18, 4), (18, 9)])
        line([(18, 13), (18, 18), (13, 18)])
        line([(9, 18), (4, 18), (4, 13)])
    elif name == "reset":
        arc = xy((4, 4, 18, 18))
        draw.arc(arc, 35, 320, fill=fg, width=2 * scale)
        line([(6, 5), (4, 10), (9, 9)])
    elif name == "clipboard":
        rect((5, 5, 17, 19))
        rect((8, 3, 14, 7), 1)
        line([(8, 11), (14, 11)], 1)
        line([(8, 15), (14, 15)], 1)
    elif name == "review":
        rect((5, 4, 17, 19))
        line([(8, 10), (10, 12), (14, 8)])
        line([(8, 16), (14, 16)], 1)
    elif name == "settings":
        cx, cy = 11, 11
        for i in range(8):
            angle = math.tau * i / 8
            line(
                [
                    (cx + math.cos(angle) * 6, cy + math.sin(angle) * 6),
                    (cx + math.cos(angle) * 8, cy + math.sin(angle) * 8),
                ],
                1,
            )
        ellipse((6, 6, 16, 16))
        ellipse((9, 9, 13, 13), 1)
    elif name == "agenda":
        rect((4, 5, 18, 18))
        line([(4, 9), (18, 9)], 1)
        line([(8, 3), (8, 7)], 1)
        line([(14, 3), (14, 7)], 1)
        draw.ellipse(xy((7, 12, 9, 14)), fill=fg)
        draw.ellipse(xy((12, 12, 14, 14)), fill=fg)
    elif name == "right-panel":
        rect((4, 4, 18, 18))
        line([(13, 4), (13, 18)], 1)
        line([(15, 8), (17, 11), (15, 14)])
    elif name == "focus":
        ellipse((5, 5, 17, 17))
        line([(11, 11), (11, 7)])
        line([(11, 11), (15, 13)])
        line([(8, 3), (14, 3)], 1)
    elif name == "theme":
        ellipse((5, 4, 17, 16))
        draw.pieslice(xy((7, 2, 21, 16)), 90, 270, fill=bg)
        line([(5, 19), (17, 19)], 1)
    elif name == "ask":
        rect((4, 5, 18, 15))
        line([(8, 15), (6, 19), (12, 15)], 1)
        line([(8, 9), (14, 9)], 1)
        line([(8, 12), (12, 12)], 1)
    elif name == "plan":
        ellipse((3, 4, 9, 10))
        ellipse((13, 4, 19, 10))
        ellipse((8, 14, 14, 20))
        line([(8, 8), (14, 8)], 1)
        line([(7, 10), (10, 15)], 1)
        line([(15, 10), (12, 15)], 1)
    elif name == "hide":
        line([(5, 11), (17, 11)])
    else:
        ellipse((5, 5, 17, 17))

    resampling = getattr(Image, "Resampling", Image)
    return image.resize((size, size), resampling.LANCZOS)
