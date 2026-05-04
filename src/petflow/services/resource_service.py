from __future__ import annotations

from petflow.domain.entities import Node
from petflow.domain.enums import NodeType
from petflow.domain.exceptions import GraphValidationError


class ResourceService:
    def resource_text(self, node: Node) -> str:
        if node.type != NodeType.RESOURCE and not node.resource_path:
            raise GraphValidationError("Selected node does not contain a resource.")
        value = node.resource_path.strip() or node.description.strip()
        if not value:
            raise GraphValidationError("Selected resource node has no content.")
        return value
