from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from calendar import monthrange

from petflow.domain.entities import Node
from petflow.domain.enums import NodeStatus, NodeType, RepeatType
from petflow.domain.graph import GraphModel


@dataclass(frozen=True, slots=True)
class AgendaDay:
    date: date
    nodes: tuple[Node, ...]


@dataclass(slots=True)
class AgendaService:
    def upcoming_days(
        self,
        graph: GraphModel,
        now: datetime | None = None,
        days: int = 7,
    ) -> list[AgendaDay]:
        local_now = (now or datetime.now().astimezone()).astimezone()
        start = local_now.date()
        grouped: dict[date, list[Node]] = {
            start + timedelta(days=offset): [] for offset in range(days)
        }

        for node in graph.nodes.values():
            if node.status == NodeStatus.DONE or node.type == NodeType.RESOURCE:
                continue
            due_date = self._scheduled_date(node, local_now)
            if due_date is None:
                continue
            for occurrence in self._occurrence_dates(node, due_date, start, days):
                grouped[occurrence].append(node)

        agenda: list[AgendaDay] = []
        for day, nodes in grouped.items():
            ordered = tuple(
                sorted(
                    nodes,
                    key=lambda node: (-node.priority, node.title.casefold()),
                )
            )
            agenda.append(AgendaDay(date=day, nodes=ordered))
        return agenda

    @staticmethod
    def _scheduled_date(node: Node, now: datetime) -> date | None:
        if not node.next_due_at:
            return None
        value = node.next_due_at.strip()
        if len(value) == 10:
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
        normalized = value.replace("Z", "+00:00")
        try:
            due_at = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if due_at.tzinfo is None:
            return due_at.date()
        return due_at.astimezone(now.tzinfo).date()

    def _occurrence_dates(
        self,
        node: Node,
        due_date: date,
        start: date,
        days: int,
    ) -> list[date]:
        end = start + timedelta(days=days)
        occurrence = due_date
        results: list[date] = []
        while occurrence < end:
            if occurrence >= start:
                results.append(occurrence)
            if node.repeat_type == RepeatType.NONE:
                break
            occurrence = self._next_occurrence(
                occurrence, node.repeat_type, node.repeat_interval
            )
        return results

    @staticmethod
    def _next_occurrence(
        occurrence: date, repeat_type: RepeatType, repeat_interval: int
    ) -> date:
        interval = max(1, repeat_interval)
        if repeat_type == RepeatType.DAILY:
            return occurrence + timedelta(days=interval)
        if repeat_type == RepeatType.WEEKLY:
            return occurrence + timedelta(weeks=interval)
        if repeat_type == RepeatType.MONTHLY:
            month_index = occurrence.month - 1 + interval
            year = occurrence.year + month_index // 12
            month = month_index % 12 + 1
            day = min(occurrence.day, monthrange(year, month)[1])
            return occurrence.replace(year=year, month=month, day=day)
        return occurrence + timedelta(days=1)
