from __future__ import annotations

import unittest

from petflow.ui.fonts import pick_ui_font_family


class FontsTest(unittest.TestCase):
    def test_pick_ui_font_family_prefers_chinese_fonts(self) -> None:
        family = pick_ui_font_family(["Arial", "Microsoft YaHei", "DejaVu Sans"])

        self.assertEqual(family, "Microsoft YaHei")

    def test_pick_ui_font_family_falls_back_to_default(self) -> None:
        family = pick_ui_font_family(["Arial", "DejaVu Sans"])

        self.assertEqual(family, "TkDefaultFont")


if __name__ == "__main__":
    unittest.main()
