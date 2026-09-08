"""Shared value objects used across the domain models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, model_validator


class TimeWindow(BaseModel):
    """A tz-aware time interval. `end` may equal `start` for an instantaneous event."""

    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _validate(self) -> "TimeWindow":
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("TimeWindow requires timezone-aware datetimes")
        if self.end < self.start:
            raise ValueError("TimeWindow.end must not be before TimeWindow.start")
        return self

    @property
    def duration_seconds(self) -> float:
        return (self.end - self.start).total_seconds()

    def overlaps(self, other: "TimeWindow") -> bool:
        return self.start <= other.end and other.start <= self.end

    def contains_instant(self, instant: datetime) -> bool:
        return self.start <= instant <= self.end
