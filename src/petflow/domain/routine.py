from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone

from petflow.domain.enums import RepeatType


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def next_due_at(
    completed_at: datetime,
    repeat_type: RepeatType,
    repeat_interval: int = 1,
) -> datetime | None:
    interval = max(1, repeat_interval)
    if repeat_type == RepeatType.DAILY:
        return completed_at + timedelta(days=interval)
    if repeat_type == RepeatType.WEEKLY:
        return completed_at + timedelta(weeks=interval)
    if repeat_type == RepeatType.MONTHLY:
        return _add_months(completed_at, interval)
    return None


def is_routine_due(
    next_due_value: str | None,
    now: datetime | None = None,
) -> bool:
    next_due = parse_iso_datetime(next_due_value)
    if next_due is None:
        return False
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return next_due <= now


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)
