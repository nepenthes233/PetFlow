from __future__ import annotations

from dataclasses import dataclass

from petflow.app.event_bus import EventBus
from petflow.app.graph_service import GraphService
from petflow.domain.graph import GraphModel
from petflow.services.pet_service import PetService
from petflow.services.recommendation_engine import RecommendationEngine
from petflow.services.storage_service import StorageService


@dataclass(slots=True)
class AppContext:
    graph: GraphModel
    graph_service: GraphService
    storage_service: StorageService
    recommendation_engine: RecommendationEngine
    pet_service: PetService
    event_bus: EventBus

    @classmethod
    def create(cls, graph: GraphModel | None = None) -> "AppContext":
        event_bus = EventBus()
        graph = graph or GraphModel()
        recommendation_engine = RecommendationEngine()
        return cls(
            graph=graph,
            graph_service=GraphService(graph=graph, event_bus=event_bus),
            storage_service=StorageService(),
            recommendation_engine=recommendation_engine,
            pet_service=PetService(graph, recommendation_engine, event_bus),
            event_bus=event_bus,
        )
