from __future__ import annotations

from collections import defaultdict, deque
from typing import Mapping

from petflow.domain.entities import Edge
from petflow.domain.enums import EdgeType


def dependency_cycle_would_form(
    edges: Mapping[str, Edge], source: str, target: str
) -> bool:
    if source == target:
        return True

    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges.values():
        if edge.type == EdgeType.DEPENDENCY:
            adjacency[edge.source].add(edge.target)
    adjacency[source].add(target)

    queue: deque[str] = deque([target])
    visited: set[str] = set()
    while queue:
        current = queue.popleft()
        if current == source:
            return True
        if current in visited:
            continue
        visited.add(current)
        for next_node in adjacency.get(current, set()):
            if next_node not in visited:
                queue.append(next_node)
    return False

