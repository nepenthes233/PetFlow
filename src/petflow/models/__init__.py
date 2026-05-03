"""Compatibility exports for older imports.

New code should import domain objects from ``petflow.domain``.
"""

from petflow.domain.entities import Edge, Node
from petflow.domain.graph import GraphModel

__all__ = ["Node", "Edge", "GraphModel"]
