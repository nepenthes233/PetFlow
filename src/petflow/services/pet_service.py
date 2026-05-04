from __future__ import annotations

from typing import TYPE_CHECKING

from petflow.domain.entities import Node, PetState
from petflow.domain.enums import EventType, NodeStatus, PetStateType
from petflow.domain.events import DomainEvent
from petflow.domain.graph import GraphModel
from petflow.services.recommendation_engine import RecommendationEngine

if TYPE_CHECKING:
    from petflow.app.event_bus import EventBus


class PetService:
    def __init__(
        self,
        graph: GraphModel,
        recommendation_engine: RecommendationEngine,
        event_bus: "EventBus",
    ) -> None:
        self.graph = graph
        self.recommendation_engine = recommendation_engine
        self.event_bus = event_bus
        self.event_bus.subscribe(EventType.NODE_UPDATED, self._on_node_updated)

    def move_to_node(
        self,
        node_id: str,
        state: PetStateType = PetStateType.MOVE,
        speech: str = "",
    ) -> PetState:
        node = self.graph.get_node(node_id)
        if node is None:
            return self.graph.pet
        self.graph.pet.current_node_id = node.id
        self.graph.pet.x = node.x + 126.0
        self.graph.pet.y = max(0.0, node.y - 26.0)
        self.graph.pet.state = state
        self.graph.pet.speech = speech
        self.graph.pet.visible = True
        self.graph.pet.touch()
        self._publish_pet_moved(node.id)
        return self.graph.pet

    def react_to_completion(self, completed_node_id: str) -> PetState:
        recommended = self.recommendation_engine.recommend_next(self.graph)
        if recommended is None:
            return self._set_idle("All clear. Pick a new node when ready.")
        return self.move_to_node(
            recommended.id,
            state=PetStateType.HAPPY,
            speech=f"Next: {recommended.title}",
        )

    def react_to_recommendation(self, node: Node | None) -> PetState:
        if node is None:
            return self._set_idle("No available next step.")
        return self.move_to_node(
            node.id,
            state=PetStateType.THINK,
            speech=f"Try this next: {node.title}",
        )

    def _on_node_updated(self, event: DomainEvent) -> None:
        if event.payload.get("field") != "status":
            return
        node_id = event.payload.get("node_id")
        status = event.payload.get("status")
        if not isinstance(node_id, str):
            return
        if status == NodeStatus.DONE.value:
            self.react_to_completion(node_id)

    def _set_idle(self, speech: str) -> PetState:
        self.graph.pet.state = PetStateType.IDLE
        self.graph.pet.speech = speech
        self.graph.pet.visible = True
        self.graph.pet.touch()
        self._publish_pet_moved(self.graph.pet.current_node_id)
        return self.graph.pet

    def _publish_pet_moved(self, node_id: str | None) -> None:
        self.event_bus.publish(
            DomainEvent(
                type=EventType.PET_MOVED,
                source="pet_service",
                payload={"node_id": node_id},
            )
        )
