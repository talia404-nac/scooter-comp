"""The validated inbound request for a day-in-the-life analysis."""

from __future__ import annotations

from datetime import date as date_, datetime, time as time_
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, field_validator, model_validator

from day_unfolded.domain.common import TimeWindow

MAX_WINDOW_HOURS = 24


class AnalysisRequest(BaseModel):
    """
    scooter_id: opaque identifier, meaning is source-specific (each source adapter
        maps this to whatever field its documentation says identifies a scooter).
    date / start_time: where the requested window begins.
    end_date / end_time: where it ends. end_date defaults to `date` (the common
        case: a window within a single day). An explicit end_date is required to
        express an overnight or multi-day span — it is never inferred from
        end_time being numerically less than start_time, since that would make
        "invalid range" indistinguishable from "overnight range" for the caller.
    timezone: IANA timezone name (e.g. "Asia/Jerusalem"). Never assumed/defaulted —
        source timestamps and the requested window must agree on timezone semantics.
    source_ids: which registered sources to query. None means "all registered
        sources" (the default, preserving prior behavior). An explicit empty
        list is rejected — that's almost certainly a caller mistake, not an
        intentional "query nothing". Membership against the actual registry
        is checked by the caller (the registry isn't known here), not by this
        model.
    """

    scooter_id: str
    date: date_
    start_time: time_
    end_date: date_ | None = None
    end_time: time_
    timezone: str
    source_ids: list[str] | None = None

    @field_validator("scooter_id")
    @classmethod
    def _scooter_id_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("scooter_id must not be blank")
        return v

    @field_validator("source_ids")
    @classmethod
    def _source_ids_valid(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("source_ids, if provided, must not be empty — omit it to query all sources")
        if any(not sid or not sid.strip() for sid in v):
            raise ValueError("source_ids must not contain blank entries")
        if len(set(v)) != len(v):
            raise ValueError("source_ids must not contain duplicates")
        return v

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown IANA timezone: {v!r}") from exc
        return v

    @property
    def window(self) -> TimeWindow:
        tz = ZoneInfo(self.timezone)
        start_dt = datetime.combine(self.date, self.start_time, tzinfo=tz)
        end_dt = datetime.combine(self.end_date or self.date, self.end_time, tzinfo=tz)
        return TimeWindow(start=start_dt, end=end_dt)

    @model_validator(mode="after")
    def _validate_window(self) -> "AnalysisRequest":
        window = self.window
        if window.duration_seconds <= 0:
            raise ValueError("requested window must have positive duration")
        if window.duration_seconds > MAX_WINDOW_HOURS * 3600:
            raise ValueError(f"requested window exceeds the {MAX_WINDOW_HOURS}h maximum")
        return self
