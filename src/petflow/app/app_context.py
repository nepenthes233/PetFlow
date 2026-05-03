from __future__ import annotations

from dataclasses import dataclass

from petflow.app.event_bus import EventBus
from petflow.app.graph_service import GraphService
from petflow.domain.graph import GraphModel
from petflow.services.recommendation_engine import RecommendationEngine
from petflow.services.storage_service import StorageService


@dataclass(slots=True)
class AppContext:
    graph: GraphModel
    graph_service: GraphService
    storage_service: StorageService
    recommendation_engine: RecommendationEngine
    event_bus: EventBus

    @classmethod
    def create(cls, graph: GraphModel | None = None) -> "AppContext":
        event_bus = EventBus()
        graph = graph or GraphModel()
        return cls(
            graph=graph,
            graph_service=GraphService(graph=graph, event_bus=event_bus),
            storage_service=StorageService(),
            recommendation_engine=RecommendationEngine(),
            event_bus=event_bus,
        )

