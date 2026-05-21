from __future__ import annotations

import unittest
from unittest.mock import patch

from petflow.system.focus_monitor import FocusMonitor


class FocusMonitorTest(unittest.TestCase):
    def test_non_windows_focus_monitor_is_unavailable(self) -> None:
        monitor = FocusMonitor()

        with patch("platform.system", return_value="Darwin"):
            self.assertIsNone(monitor.current_window_title())
            self.assertFalse(monitor.is_available())


if __name__ == "__main__":
    unittest.main()
