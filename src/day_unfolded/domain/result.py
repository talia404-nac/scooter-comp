"""The structured, machine-readable result of a full analysis run.

This is the boundary artifact: the deterministic pipeline produces exactly
this, the Hebrew presenter consumes only this (never raw observations or raw
source records), and a future map UI would consume only this too.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from day_unfolded.domain.common import TimeWindow
from day_unfolded.domain.observation import LocationObservation
from day_unfolded.domain.timeline import (
    Anomaly,
    Conflict,
    CorroborationGroup,
    DuplicateGroup,
    Gap,
    TimelineSegment,
)


class SourceStatusCode(str, Enum):
    OK = "ok"
    NO_DATA = "no_data"
    FAILED = "failed"
    TIMEOUT = "timeout"
    MALFORMED_DATA = "malformed_data"


class SourceStatus(BaseModel):
    source_id: str
    status: SourceStatusCode
    record_count: int = 0
    observation_count: int = 0
    error: str | None = None


class AnalysisResult(BaseModel):
    scooter_id: str
    window: TimeWindow

    observations: list[LocationObservation] = Field(default_factory=list)
    segments: list[TimelineSegment] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    anomalies: list[Anomaly] = Field(default_factory=list)
    duplicates: list[DuplicateGroup] = Field(default_factory=list)
    corroborations: list[CorroborationGroup] = Field(default_factory=list)

    source_statuses: list[SourceStatus] = Field(default_factory=list)
