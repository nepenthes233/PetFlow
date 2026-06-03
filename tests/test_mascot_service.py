from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from petflow.services import MascotService


class MascotServiceTest(unittest.TestCase):
    def test_loads_image_mascot_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mascots_dir = Path(directory)
            mascot_dir = mascots_dir / "anime_assistant"
            mascot_dir.mkdir()
            (mascot_dir / "idle.png").write_bytes(b"not a real png")
            (mascot_dir / "mascot.json").write_text(
                json.dumps(
                    {
                        "id": "anime_assistant",
                        "name": "Anime Assistant",
                        "type": "image",
                        "size": [88, 108],
                        "states": {"idle": "idle.png"},
                    }
                ),
                encoding="utf-8",
            )

            config = MascotService(mascots_dir).load("anime_assistant")

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.id, "anime_assistant")
        self.assertEqual(config.size, (88, 108))
        self.assertEqual(config.asset_path("focused").name, "idle.png")

    def test_load_falls_back_to_default_mascot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mascots_dir = Path(directory)
            mascot_dir = mascots_dir / "line_dog"
            mascot_dir.mkdir()
            (mascot_dir / "idle.png").write_bytes(b"not a real png")
            (mascot_dir / "mascot.json").write_text(
                json.dumps(
                    {
                        "id": "line_dog",
                        "name": "Line Dog",
                        "type": "image",
                        "states": {"idle": "idle.png"},
                    }
                ),
                encoding="utf-8",
            )

            config = MascotService(mascots_dir).load("missing")

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.id, "line_dog")

    def test_ignores_config_without_existing_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mascots_dir = Path(directory)
            mascot_dir = mascots_dir / "broken"
            mascot_dir.mkdir()
            (mascot_dir / "mascot.json").write_text(
                json.dumps(
                    {
                        "id": "broken",
                        "name": "Broken",
                        "type": "image",
                        "states": {"idle": "missing.png"},
                    }
                ),
                encoding="utf-8",
            )

            config = MascotService(mascots_dir, default_mascot_id="broken").load()

        self.assertIsNone(config)

    def test_rejects_state_asset_paths_outside_mascot_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mascots_dir = Path(directory)
            mascot_dir = mascots_dir / "unsafe"
            mascot_dir.mkdir()
            (mascot_dir / "mascot.json").write_text(
                json.dumps(
                    {
                        "id": "unsafe",
                        "name": "Unsafe",
                        "type": "image",
                        "states": {"idle": "../idle.png"},
                    }
                ),
                encoding="utf-8",
            )

            config = MascotService(mascots_dir, default_mascot_id="unsafe").load()

        self.assertIsNone(config)

    def test_user_mascot_directory_overrides_bundled_directory(self) -> None:
        with tempfile.TemporaryDirectory() as user_directory:
            with tempfile.TemporaryDirectory() as bundled_directory:
                user_mascot_dir = Path(user_directory) / "same_id"
                bundled_mascot_dir = Path(bundled_directory) / "same_id"
                user_mascot_dir.mkdir()
                bundled_mascot_dir.mkdir()
                (user_mascot_dir / "idle.png").write_bytes(b"not a real png")
                (bundled_mascot_dir / "idle.png").write_bytes(b"not a real png")
                (user_mascot_dir / "mascot.json").write_text(
                    json.dumps(
                        {
                            "id": "same_id",
                            "name": "User Theme",
                            "type": "image",
                            "states": {"idle": "idle.png"},
                        }
                    ),
                    encoding="utf-8",
                )
                (bundled_mascot_dir / "mascot.json").write_text(
                    json.dumps(
                        {
                            "id": "same_id",
                            "name": "Bundled Theme",
                            "type": "image",
                            "states": {"idle": "idle.png"},
                        }
                    ),
                    encoding="utf-8",
                )

                service = MascotService(
                    default_mascot_id="same_id",
                    mascot_dirs=[Path(user_directory), Path(bundled_directory)],
                )
                config = service.load()
                configs = service.list_configs()

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.name, "User Theme")
        self.assertEqual([listed.name for listed in configs], ["User Theme"])


if __name__ == "__main__":
    unittest.main()
