from __future__ import annotations

import unittest

from petflow.system.clipboard_watcher import ClipboardWatcher


class ClipboardWatcherTest(unittest.TestCase):
    def test_capture_url(self) -> None:
        watcher = ClipboardWatcher()

        capture = watcher.capture_once(lambda: "https://example.com/path")

        self.assertIsNotNone(capture)
        assert capture is not None
        self.assertEqual(capture.resource_type, "url")
        self.assertEqual(capture.title, "example.com")
        self.assertEqual(capture.content, "https://example.com/path")

    def test_capture_text(self) -> None:
        watcher = ClipboardWatcher()

        capture = watcher.capture_once(lambda: "Remember to write tests\nSecond line")

        self.assertIsNotNone(capture)
        assert capture is not None
        self.assertEqual(capture.resource_type, "text")
        self.assertEqual(capture.title, "Remember to write tests")

    def test_empty_clipboard_returns_none(self) -> None:
        watcher = ClipboardWatcher()

        self.assertIsNone(watcher.capture_once(lambda: "   "))


if __name__ == "__main__":
    unittest.main()
