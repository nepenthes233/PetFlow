from __future__ import annotations

from collections.abc import Iterable
import tkinter as tk
from tkinter import font as tkfont

PREFERRED_UI_FONTS = (
    "Segoe UI",
    "PingFang SC",
    "Hiragino Sans GB",
    "Heiti SC",
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
    "SimHei",
)

_NAMED_FONTS = (
    "TkDefaultFont",
    "TkTextFont",
    "TkMenuFont",
    "TkHeadingFont",
    "TkCaptionFont",
    "TkSmallCaptionFont",
    "TkIconFont",
    "TkTooltipFont",
)


def pick_ui_font_family(available_families: Iterable[str]) -> str:
    available = set(available_families)
    for family in PREFERRED_UI_FONTS:
        if family in available:
            return family
    return "TkDefaultFont"


def get_ui_font_family(master: tk.Misc | None = None) -> str:
    try:
        return pick_ui_font_family(tkfont.families(master))
    except tk.TclError:
        return "TkDefaultFont"


def apply_ui_font_defaults(master: tk.Misc | None = None) -> str:
    family = get_ui_font_family(master)
    for font_name in _NAMED_FONTS:
        try:
            tkfont.nametofont(font_name).configure(family=family)
        except tk.TclError:
            continue
    return family
