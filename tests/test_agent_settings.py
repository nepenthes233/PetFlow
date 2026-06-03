from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from petflow.agent.agent_client import AgentClient
from petflow.agent.settings import AgentSettings


class AgentSettingsTest(unittest.TestCase):
    def test_save_and_load_settings(self) -> None:
        settings = AgentSettings(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="demo-model",
            wire_api="responses",
            mock_mode=True,
            mascot_id="anime_assistant",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            settings.save(path)

            loaded = AgentSettings.load(path)

        self.assertEqual(loaded.api_key, "test-key")
        self.assertEqual(loaded.base_url, "https://api.example.com/v1")
        self.assertEqual(loaded.model, "demo-model")
        self.assertEqual(loaded.wire_api, "responses")
        self.assertTrue(loaded.mock_mode)
        self.assertEqual(loaded.mascot_id, "anime_assistant")

    def test_client_uses_settings(self) -> None:
        settings = AgentSettings(
            api_key="settings-key",
            base_url="https://api.example.com/v1",
            model="demo-model",
            wire_api="responses",
            mock_mode=False,
        )

        client = AgentClient.from_settings(settings)

        self.assertEqual(client.api_key, "settings-key")
        self.assertEqual(client.base_url, "https://api.example.com/v1")
        self.assertEqual(client.model, "demo-model")
        self.assertEqual(client.wire_api, "responses")
        self.assertFalse(client.mock_mode)

    def test_settings_and_client_strip_credentials_and_base_url(self) -> None:
        settings = AgentSettings(
            api_key="  sk-test-last  ",
            base_url="  https://api.deepseek.com/  ",
            model=" deepseek-chat ",
            wire_api=" chat_completions ",
        )

        client = AgentClient.from_settings(settings)

        self.assertEqual(client.api_key, "sk-test-last")
        self.assertEqual(client.base_url, "https://api.deepseek.com")
        self.assertEqual(client.model, "deepseek-chat")
        self.assertEqual(client.wire_api, "chat_completions")


if __name__ == "__main__":
    unittest.main()
