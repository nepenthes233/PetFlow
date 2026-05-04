from __future__ import annotations

import platform


class FocusMonitor:
    def current_window_title(self) -> str | None:
        if platform.system() != "Windows":
            return None
        try:
            import win32gui  # type: ignore[import-not-found]
        except ImportError:
            return None
        window = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(window)
        return title or None

    def is_available(self) -> bool:
        if platform.system() != "Windows":
            return False
        try:
            import win32gui  # type: ignore[import-not-found]
        except ImportError:
            return False
        return True
        return None
