"""Timeline-level structures produced by the deterministic analysis engine.

These are all *outputs* of analysis — nothing in this module is ever populated
by guessing. A field is only set when a preceding deterministic calculation
produced it (e.g. `direction` is None whenever fewer than two located
observations were available to compute a bearing from).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MovementState(str, Enum):
    STATIONARY = "stationary"
    MOVING = "moving"
    # Used when a segment has a location but not enough consecutive observations
    # to classify movement (e.g. a single instantaneous observation).
    UNKNOWN = "unknown"


class Direction(str, Enum):
    N = "N"
    NE = "NE"
    E = "E"
    SE = "SE"
    S = "S"
    SW = "SW"
    W = "W"
    NW = "NW"


class TimelineSegment(BaseModel):
    start_time: datetime
    end_time: datetime
    state: MovementState

    representative_latitude: float | None = None
    representative_longitude: float | None = None

    # Only set for MOVING segments backed by >=2 located observations.
    direction: Direction | None = None
    distance_meters: float | None = None
    speed_mps: float | None = None

    supporting_observation_ids: list[str]
    source_ids: list[str]


class Gap(BaseModel):
    """An interval within the requested window with no covering observation.
    Never filled or inferred — the absence itself is the fact being recorded."""

    start_time: datetime
    end_time: datetime


class ConflictObservationRef(BaseModel):
    observation_id: str
    source_id: str
    latitude: float
    longitude: float
    time: datetime


class Conflict(BaseModel):
    """Two or more sources reporting materially different locations for
    overlapping time. No winner is chosen at this layer."""

    start_time: datetime
    end_time: datetime
    observations: list[ConflictObservationRef] = Field(min_length=2)


class Anomaly(BaseModel):
    """Consecutive observations imply a physically implausible speed.
    Flagged, not corrected — no intermediate route is invented."""

    from_observation_id: str
    to_observation_id: str
    distance_meters: float
    elapsed_seconds: float
    implied_speed_mps: float
    max_reasonable_speed_mps: float


class DuplicateGroup(BaseModel):
    """Same underlying event reported more than once (same source, same
    record/near-identical report). Collapsed for presentation; every member
    id is retained so provenance is never lost."""

    kept_observation_id: str
    duplicate_observation_ids: list[str]


class CorroborationGroup(BaseModel):
    """Two or more independent sources agreeing on materially the same
    location for overlapping time."""

    start_time: datetime
    end_time: datetime
    observation_ids: list[str]
    source_ids: list[str]
