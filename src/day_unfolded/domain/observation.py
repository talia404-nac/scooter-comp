"""The canonical observation model.

Every source adapter, regardless of how alien its raw record format is, must
produce a list of these. The analysis engine only ever sees LocationObservation —
never a raw source record and never a source-specific field name.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class OriginType(str, Enum):
    """Whether the location was reported directly by the source, or derived by
    applying that source's documented interpretation rules to a non-location fact."""

    DIRECT = "direct"
    DERIVED = "derived"


class LocationObservation(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    scooter_id: str

    # Instantaneous observations set start_time == end_time.
    start_time: datetime
    end_time: datetime

    latitude: float | None = None
    longitude: float | None = None

    origin_type: OriginType
    # Required and populated only when origin_type == DERIVED: names the rule from
    # that source's documented interpretation used to derive this location
    # (e.g. "cell_tower_lookup"). Never left implicit — a derived observation must
    # never be indistinguishable from a direct one.
    derivation: str | None = None

    source_id: str
    source_record_ref: str

    uncertainty_meters: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("latitude")
    @classmethod
    def _valid_latitude(cls, v: float | None) -> float | None:
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError(f"latitude out of range: {v}")
        return v

    @field_validator("longitude")
    @classmethod
    def _valid_longitude(cls, v: float | None) -> float | None:
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError(f"longitude out of range: {v}")
        return v

    @model_validator(mode="after")
    def _validate(self) -> "LocationObservation":
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("LocationObservation requires timezone-aware datetimes")
        if self.end_time < self.start_time:
            raise ValueError("end_time must not be before start_time")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be present or both absent")
        if self.origin_type is OriginType.DERIVED and not self.derivation:
            raise ValueError("derived observations must state their derivation rule")
        if self.origin_type is OriginType.DIRECT and self.derivation:
            raise ValueError("direct observations must not carry a derivation rule")
        return self

    @property
    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def midpoint_time(self) -> datetime:
        return self.start_time + (self.end_time - self.start_time) / 2
