from __future__ import annotations

from uuid import uuid4


class IdGenerator:
    def node_id(self) -> str:
        return f"node_{uuid4().hex[:12]}"

    def edge_id(self) -> str:
        return f"edge_{uuid4().hex[:12]}"

    def checklist_item_id(self) -> str:
        return f"check_{uuid4().hex[:12]}"

