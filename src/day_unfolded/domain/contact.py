"""Customer contact events: calls and messages about a scooter.

These are deliberately NOT LocationObservations. A customer call or message
carries no positional fact the way a GPS ping or cell-tower lookup does —
forcing one into LocationObservation (even with latitude/longitude left
None) would blur what that model means and let contact events leak into
segmentation/gap/conflict analysis, which must only ever reason about actual
location facts. Contact events are a separate, parallel stream that gets
merged into AnalysisResult and shown alongside the location timeline for
presentation only — analysis/*.py never sees them.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ContactChannel(str, Enum):
    CALL = "call"
    MESSAGE = "message"


class CustomerContactEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    scooter_id: str

    time: datetime
    channel: ContactChannel
    # Verbatim content from the source (call notes/transcript summary, or
    # message text) — never paraphrased or interpreted by this layer.
    summary: str

    source_id: str
    source_record_ref: str

    @field_validator("summary")
    @classmethod
    def _summary_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("summary must not be blank")
        return v

    @field_validator("time")
    @classmethod
    def _tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("CustomerContactEvent.time requires a timezone-aware datetime")
        return v
