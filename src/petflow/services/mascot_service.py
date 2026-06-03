from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from petflow.config import DEFAULT_MASCOT_ID, MASCOTS_DIR, USER_MASCOTS_DIR


@dataclass(frozen=True)
class MascotConfig:
    id: str
    name: str
    type: str
    root: Path
    size: tuple[int, int]
    states: dict[str, str]

    def asset_path(self, state: str) -> Path | None:
        filename = self.states.get(state) or self.states.get("idle")
        if filename is None:
            return None
        return self.root / filename


class MascotService:
    def __init__(
        self,
        mascots_dir: Path | None = None,
        default_mascot_id: str = DEFAULT_MASCOT_ID,
        mascot_dirs: Sequence[Path] | None = None,
    ) -> None:
        if mascot_dirs is not None:
            self.mascot_dirs = list(mascot_dirs)
        elif mascots_dir is not None:
            self.mascot_dirs = [mascots_dir]
        else:
            self.mascot_dirs = [USER_MASCOTS_DIR, MASCOTS_DIR]
        self.default_mascot_id = default_mascot_id

    def load(self, mascot_id: str | None = None) -> MascotConfig | None:
        if mascot_id:
            config = self._load_by_id(mascot_id)
            if config is not None:
                return config
        return self._load_by_id(self.default_mascot_id)

    def list_configs(self) -> list[MascotConfig]:
        configs: list[MascotConfig] = []
        seen: set[str] = set()
        for mascots_dir in self.mascot_dirs:
            if not mascots_dir.exists():
                continue
            for path in sorted(mascots_dir.glob("*/mascot.json")):
                config = self._load_file(path)
                if config is not None and config.id not in seen:
                    configs.append(config)
                    seen.add(config.id)
        return configs

    def _load_by_id(self, mascot_id: str) -> MascotConfig | None:
        for mascots_dir in self.mascot_dirs:
            config = self._load_file(mascots_dir / mascot_id / "mascot.json")
            if config is not None:
                return config
        return None

    def _load_file(self, path: Path) -> MascotConfig | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            config = self._parse_config(data, path.parent)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None
        if not self._has_usable_asset(config):
            return None
        return config

    def _parse_config(self, data: dict[str, Any], root: Path) -> MascotConfig:
        mascot_id = self._required_string(data, "id")
        name = self._required_string(data, "name")
        mascot_type = self._required_string(data, "type")
        if mascot_type != "image":
            raise ValueError(f"Unsupported mascot type: {mascot_type}")

        states_data = data.get("states")
        if not isinstance(states_data, dict):
            raise ValueError("Mascot states must be an object.")
        states = {
            str(key): value
            for key, value in states_data.items()
            if isinstance(value, str) and value
        }
        if not states:
            raise ValueError("Mascot requires at least one state asset.")
        for filename in states.values():
            asset_path = Path(filename)
            if asset_path.is_absolute() or ".." in asset_path.parts:
                raise ValueError(
                    "Mascot state assets must stay inside the mascot folder."
                )

        size_data = data.get("size", [88, 108])
        if (
            not isinstance(size_data, list)
            or len(size_data) != 2
            or not all(isinstance(value, int) and value > 0 for value in size_data)
        ):
            raise ValueError("Mascot size must contain two positive integers.")

        return MascotConfig(
            id=mascot_id,
            name=name,
            type=mascot_type,
            root=root,
            size=(size_data[0], size_data[1]),
            states=states,
        )

    @staticmethod
    def _required_string(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"Mascot {key} must be a non-empty string.")
        return value

    @staticmethod
    def _has_usable_asset(config: MascotConfig) -> bool:
        return any(config.asset_path(state).exists() for state in config.states)
