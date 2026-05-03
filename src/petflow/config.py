from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
DEFAULT_GRAPH_PATH = DATA_DIR / "graph.json"


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "PetFlow"
    window_width: int = 1200
    window_height: int = 800
    min_width: int = 960
    min_height: int = 640
